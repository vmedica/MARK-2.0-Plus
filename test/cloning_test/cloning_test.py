"""Black-box system testing for MARK 2.0 repository cloning using CLI interface."""

"""Running with the command: pytest .\cloning_test.py -v """
import subprocess
import sys
from pathlib import Path
import pytest
import pandas as pd
import shutil


# ============================================================================
# FIXTURES & UTILITIES
# ============================================================================


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """Get path to test data directory containing CSV files."""
    return project_root / "test" / "cloning_test" / "test_data"


@pytest.fixture
def io_structure(tmp_path, project_root):
    """Setup IO structure for cloning tests."""
    io_path = tmp_path / "io"
    io_path.mkdir()

    # Copy library dictionaries
    src_lib_dict = project_root / "io" / "library_dictionary"
    dst_lib_dict = io_path / "library_dictionary"
    if src_lib_dict.exists():
        shutil.copytree(src_lib_dict, dst_lib_dict)

    # Clean cloner logs from project root
    cloner_log_dir = project_root / "modules" / "cloner" / "log"
    if cloner_log_dir.exists():
        for log_file in ["cloned_log.csv"]:
            log_path = cloner_log_dir / log_file
            if log_path.exists():
                log_path.unlink()

    return io_path


def run_main_cli(project_root, **kwargs):
    """Execute main_args.py with CLI arguments.

    Args:
        project_root: Path to project root
        **kwargs: CLI arguments as key-value pairs

    Returns:
        subprocess.CompletedProcess
    """
    cmd = [sys.executable, str(project_root / "main_args.py")]

    # Convert kwargs to CLI arguments
    for key, value in kwargs.items():
        arg_name = f"--{key.replace('_', '-')}"

        if isinstance(value, bool):
            if value:
                cmd.append(arg_name)
        elif isinstance(value, (Path, str)):
            cmd.extend([arg_name, str(value)])
        elif isinstance(value, int):
            cmd.extend([arg_name, str(value)])

    result = subprocess.run(
        cmd, cwd=project_root, capture_output=True, text=True, timeout=600
    )

    return result


def count_cloned_repos(repos_path):
    """Count number of successfully cloned repositories.

    Args:
        repos_path: Path to repos directory

    Returns:
        int: Number of cloned repositories
    """
    if not repos_path.exists():
        return 0

    count = 0
    for owner_dir in repos_path.iterdir():
        if owner_dir.is_dir():
            for repo_dir in owner_dir.iterdir():
                if repo_dir.is_dir() and (repo_dir / ".git").exists():
                    count += 1

    return count


def get_cloned_repo_names(repos_path):
    """Get list of cloned repository names.

    Args:
        repos_path: Path to repos directory

    Returns:
        set: Set of repository names in format "owner/repo"
    """
    if not repos_path.exists():
        return set()

    cloned = set()
    for owner_dir in repos_path.iterdir():
        if owner_dir.is_dir():
            owner = owner_dir.name
            for repo_dir in owner_dir.iterdir():
                if repo_dir.is_dir() and (repo_dir / ".git").exists():
                    cloned.add(f"{owner}/{repo_dir.name}")

    return cloned


# ============================================================================
# TEST CLASS
# ============================================================================


class TestCloningBlackBox:
    """Black-box system tests for repository cloning using CLI interface."""

    def test_1_csv_not_exists(self, project_root, io_structure):
        """TF1: File CSV non esiste → Messaggio d'errore"""
        nonexistent_csv = io_structure / "nonexistent.csv"
        repos_path = io_structure / "repos"

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            project_list=nonexistent_csv,
            repository_path=repos_path,
            n_repos=10,
            clone=True,
        )

        assert (
            result.returncode != 0
        ), f"Expected non-zero return code for missing CSV, got {result.returncode}"

        error_output = result.stderr.lower()
        assert any(
            err in error_output
            for err in [
                "project list file not found",
            ]
        ), f"Expected error about missing CSV file.\nStderr: {result.stderr}"

    def test_2_csv_empty(self, project_root, io_structure, test_data_dir):
        """TF2: CSV vuoto (solo header) → Nessun repository clonato."""
        empty_csv = test_data_dir / "TF2" / "empty_projects.csv"
        repos_path = io_structure / "repos"

        if not empty_csv.exists():
            pytest.skip(f"Test data not found: {empty_csv}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            project_list=empty_csv,
            repository_path=repos_path,
            n_repos=10,
            clone=True,
        )

        assert result.returncode == 0, (
            f"Execution failed with code {result.returncode}\n"
            f"Stderr: {result.stderr}\nStdout: {result.stdout}"
        )

        # Verify no repositories were cloned
        cloned_count = count_cloned_repos(repos_path)
        assert (
            cloned_count == 0
        ), f"Expected 0 cloned repos from empty CSV, found {cloned_count}"

    def test_3_csv_single_repo(self, project_root, io_structure, test_data_dir):
        """TF3: CSV con 1 repository → 1 repository clonato correttamente."""
        single_csv = test_data_dir / "TF3" / "single_project.csv"
        repos_path = io_structure / "repos"

        if not single_csv.exists():
            pytest.skip(f"Test data not found: {single_csv}")

        # Read expected repository name
        df = pd.read_csv(single_csv)
        if df.empty:
            pytest.skip("CSV file is empty")

        expected_repo = df.iloc[0]["ProjectName"]

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            project_list=single_csv,
            repository_path=repos_path,
            n_repos=1,
            clone=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        # Verify exactly 1 repository was cloned
        cloned_count = count_cloned_repos(repos_path)
        assert cloned_count == 1, f"Expected 1 cloned repo, found {cloned_count}"

        # Verify correct repository was cloned
        cloned_repos = get_cloned_repo_names(repos_path)
        assert (
            expected_repo in cloned_repos
        ), f"Expected {expected_repo} to be cloned, but found: {cloned_repos}"

    def test_4_csv_multiple_repos(self, project_root, io_structure, test_data_dir):
        """TF4: CSV con N repository (N > 1) → N repository clonati correttamente."""
        multi_csv = test_data_dir / "TF4" / "multi_projects.csv"
        repos_path = io_structure / "repos"

        if not multi_csv.exists():
            pytest.skip(f"Test data not found: {multi_csv}")

        # Read expected repositories
        df = pd.read_csv(multi_csv)
        n_repos = len(df)

        if n_repos <= 1:
            pytest.skip("CSV file does not contain multiple repositories")

        expected_repos = set(df["ProjectName"].tolist())

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            project_list=multi_csv,
            repository_path=repos_path,
            n_repos=n_repos,
            clone=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        # Verify all repositories were cloned
        cloned_count = count_cloned_repos(repos_path)
        assert (
            cloned_count == n_repos
        ), f"Expected {n_repos} cloned repos, found {cloned_count}"

        # Verify correct repositories were cloned
        cloned_repos = get_cloned_repo_names(repos_path)
        assert (
            cloned_repos == expected_repos
        ), f"Expected repos {expected_repos}, but found: {cloned_repos}"
