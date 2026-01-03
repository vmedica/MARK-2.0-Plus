"""Black-box system testing for MARK 2.0 analysis function using CLI interface."""

"""Running with the command: pytest .\analysis_test.py -v """

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
def test_repo_dir(project_root):
    """Get path to test data repositories."""
    return project_root / "test" / "analysis_test" / "test_repos"


@pytest.fixture
def io_structure(tmp_path, project_root):
    """Setup IO structure with library dictionaries."""
    io_path = tmp_path / "io"
    io_path.mkdir()

    # Copy library dictionaries
    src_lib_dict = project_root / "io" / "library_dictionary"
    dst_lib_dict = io_path / "library_dictionary"
    if src_lib_dict.exists():
        shutil.copytree(src_lib_dict, dst_lib_dict)

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
        cmd, cwd=project_root, capture_output=True, text=True, timeout=300
    )

    return result


def get_classified_projects(io_path, role):
    """Get set of unique project names classified as the given role.

    Args:
        io_path: Path to IO directory
        role: 'producer' or 'consumer'

    Returns:
        set: Set of unique project names classified as ML role
    """
    result_dir = io_path / "output" / role / f"{role}_1"

    if not result_dir.exists():
        return set()

    results_csv = result_dir / "results.csv"
    if not results_csv.exists():
        return set()

    df = pd.read_csv(results_csv)
    if df.empty:
        return set()

    column_name = f"Is ML {role}"
    if column_name not in df.columns:
        return set()

    # Get unique projects where classification is "Yes"
    classified = df[df[column_name].str.contains("Yes", case=False, na=False)][
        "ProjectName"
    ].unique()

    return set(classified)


# ============================================================================
# TEST CLASS
# ============================================================================


class TestAnalysisBlackBox:
    """Black-box system tests using CLI interface."""

    def test_1_invalid_directory(self, project_root, io_structure, tmp_path):
        """TF1: Directory non esiste → Messaggio d'errore."""
        nonexistent = tmp_path / "does_not_exist"

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=nonexistent,
            analysis=True,
        )

        # (return 0 of the main) returncode != 0 indicates a command error or failure.
        assert (
            result.returncode != 0
        ), f"Expected non-zero return code, got {result.returncode}"

        # Prepare error output by converting it to lowercase
        error_output = result.stderr.lower()
        
        # Check: if the command error message contains the specific string then the test passes
        assert any(
            err in error_output
            for err in [
                "input folder not found",
            ]
        ), f"Expected error about missing directory.\nStderr: {result.stderr}"

    def test_2_empty_directory(self, project_root, io_structure, tmp_path):
        """TF2: Directory vuota → Nessun progetto classificato."""
        empty_repos = tmp_path / "empty_repos"
        empty_repos.mkdir()

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=empty_repos,
            analysis=True,
        )

        assert result.returncode == 0, (
            f"Execution failed with code {result.returncode}\n"
            f"Stderr: {result.stderr}\nStdout: {result.stdout}"
        )

        producers = get_classified_projects(io_structure, "producer")
        consumers = get_classified_projects(io_structure, "consumer")

        assert len(producers) == 0, f"Expected 0 producers, found {len(producers)}"
        assert len(consumers) == 0, f"Expected 0 consumers, found {len(consumers)}"

    def test_3_single_non_ml(self, project_root, io_structure, test_repo_dir):
        """TF3: 1 progetto non-ML → Non classificato."""
        test_repos = test_repo_dir / "TF3"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        """Verifies that the exit code is exactly 0, which means the CLI command 
        (main_args.py --analysis True --io-path ... --repository-path ...) 
        completed without errors. 
        If the assertion fails, an AssertionError exception is raised with 
        a message that includes the standard error output (stderr) of the 
        failed process."""
        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        producers = get_classified_projects(io_structure, "producer")
        consumers = get_classified_projects(io_structure, "consumer")

        assert (
            len(producers) == 0
        ), f"Non-ML project should not be classified as producer. Found: {producers}"
        assert (
            len(consumers) == 0
        ), f"Non-ML project should not be classified as consumer. Found: {consumers}"

    def test_4_single_producer(self, project_root, io_structure, test_repo_dir):
        """TF4: 1 progetto Producer → Classificato Producer."""
        test_repos = test_repo_dir / "TF4"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        producers = get_classified_projects(io_structure, "producer")
        consumers = get_classified_projects(io_structure, "consumer")

        assert (
            len(producers) == 1
        ), f"Expected 1 producer, found {len(producers)}: {producers}"
        assert (
            len(consumers) == 0
        ), f"Expected 0 consumers, found {len(consumers)}: {consumers}"

    def test_5_single_consumer(self, project_root, io_structure, test_repo_dir):
        """TF5: 1 progetto Consumer → Classificato Consumer."""
        test_repos = test_repo_dir / "TF5"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        producers = get_classified_projects(io_structure, "producer")
        consumers = get_classified_projects(io_structure, "consumer")

        assert (
            len(producers) == 0
        ), f"Expected 0 producers, found {len(producers)}: {producers}"
        assert (
            len(consumers) == 1
        ), f"Expected 1 consumer, found {len(consumers)}: {consumers}"

    def test_6_single_hybrid(self, project_root, io_structure, test_repo_dir):
        """TF6: 1 progetto Producer+Consumer → Classificato entrambi."""
        test_repos = test_repo_dir / "TF6"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        producers = get_classified_projects(io_structure, "producer")
        consumers = get_classified_projects(io_structure, "consumer")

        assert (
            len(producers) == 1
        ), f"Hybrid project should be classified as producer. Found: {producers}"
        assert (
            len(consumers) == 1
        ), f"Hybrid project should be classified as consumer. Found: {consumers}"

    def test_7_multi_non_ml(self, project_root, io_structure, test_repo_dir):
        """TF7: Multi progetti non-ML → Nessuno classificato."""
        test_repos = test_repo_dir / "TF7"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        producers = get_classified_projects(io_structure, "producer")
        consumers = get_classified_projects(io_structure, "consumer")

        assert len(producers) == 0, f"Expected 0 producers, found {len(producers)}"
        assert len(consumers) == 0, f"Expected 0 consumers, found {len(consumers)}"

    def test_8_multi_with_producer(self, project_root, io_structure, test_repo_dir):
        """TF8: Multi progetti con almeno 1 Producer."""
        test_repos = test_repo_dir / "TF8"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        producers = get_classified_projects(io_structure, "producer")

        assert (
            len(producers) >= 1
        ), f"Expected at least 1 producer, found {len(producers)}"

    def test_9_multi_with_consumer(self, project_root, io_structure, test_repo_dir):
        """TF9: Multi progetti con almeno 1 Consumer."""
        test_repos = test_repo_dir / "TF9"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        consumers = get_classified_projects(io_structure, "consumer")

        assert (
            len(consumers) >= 1
        ), f"Expected at least 1 consumer, found {len(consumers)}"

    def test_10_multi_mixed(self, project_root, io_structure, test_repo_dir):
        """TF10: Multi progetti con Producer E Consumer."""
        test_repos = test_repo_dir / "TF10"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        producers = get_classified_projects(io_structure, "producer")
        consumers = get_classified_projects(io_structure, "consumer")

        assert (
            len(producers) >= 1
        ), f"Expected at least 1 producer, found {len(producers)}"
        assert (
            len(consumers) >= 1
        ), f"Expected at least 1 consumer, found {len(consumers)}"

    def test_11_multi_producers(self, project_root, io_structure, test_repo_dir):
        """TF11: Multi progetti con 2+ Producer."""
        test_repos = test_repo_dir / "TF11"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        producers = get_classified_projects(io_structure, "producer")

        assert (
            len(producers) >= 2
        ), f"Expected at least 2 producers, found {len(producers)}: {producers}"

    def test_12_multi_consumers(self, project_root, io_structure, test_repo_dir):
        """TF12: Multi progetti con 2+ Consumer."""
        test_repos = test_repo_dir / "TF12"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            analysis=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        consumers = get_classified_projects(io_structure, "consumer")

        assert (
            len(consumers) >= 2
        ), f"Expected at least 2 consumers, found {len(consumers)}: {consumers}"
