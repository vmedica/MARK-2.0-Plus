# For execution, use the command: pytest -vv -s .\test\system_test_metrics\system_test_metrics.py

"""
Black-box system testing for MARK 2.0 metrics function using CLI interface.
Running with the command: pytest -v

Test Cases:
-TC1: Directory does not exist -> Error message "Input folder not found"
-TC2: Empty directory -> No metrics calculated
-TC3: More projects without Python files -> MI = 0 and CC = 0
-TC4: Multiple projects with empty Python files -> MI = 0 and CC = 0
-TC5: Multiple projects with Python files with valid code -> MI > 0 and CC > 0
-TC6: Mix of projects -> MI and CC = 0 or > 0 based on content
"""

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
    """Get project root directory (MARK-2.0-Plus)."""
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def test_repo_dir(project_root):
    """Get path to test data repositories."""
    return project_root / "test" / "system_testing" / "metrics_test" / "test_repos"


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


def get_metrics_projects(io_path, role="metrics"):
    """Get metrics data for all analyzed projects.

    Args:
        io_path: Path to IO directory
        role: Role folder name (default: 'metrics')

    Returns:
        dict: Dictionary with project names as keys and dict of metrics as values
              Format: {"project_name": {"CC_avg": value, "MI_avg": value}}
              Returns empty dict if no results found
    """
    result_dir = io_path / "output" / role / f"{role}_1"

    if not result_dir.exists():
        return {}

    results_csv = result_dir / "metrics.csv"
    if not results_csv.exists():
        return {}

    df = pd.read_csv(results_csv)

    # Build dictionary with project name as key and metrics as value
    metrics_dict = {}
    for _, row in df.iterrows():
        project_name = row["ProjectName"]
        metrics_dict[project_name] = {"CC_avg": row["CC_avg"], "MI_avg": row["MI_avg"]}

    return metrics_dict


# ============================================================================
# TEST CLASS
# ============================================================================


class TestMetricsBlackBox:
    """Black-box system tests for metrics calculation using CLI interface."""

    # ------------------------------------------------------------------------
    # TC1: Non-existent directory -> Error message "Input folder not found"
    # ------------------------------------------------------------------------
    def test_tc1_invalid_directory(self, project_root, io_structure, tmp_path):
        """TC1: Directory does not exist -> Error message.

        Test Case ID: TC1
        Input: "repo_does_not_exist" (non-existent directory)
        Environment description: Non-existent directory
        Oracle: Error message "Input folder not found" is returned
        """
        nonexistent = tmp_path / "repo_does_not_exist"

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=nonexistent,
            metrics=True,
        )

        # returncode != 0 indicates a command error
        assert (
            result.returncode != 0
        ), f"Expected non-zero return code, got {result.returncode}"

        # Verify error message in stderr (case-insensitive)
        error_output = result.stderr.lower()

        assert "input folder not found" in error_output, (
            f"Expected error message 'input folder not found' in stderr.\n"
            f"Stderr: {result.stderr}"
        )

    # ------------------------------------------------------------------------
    # TC2: Empty directory -> No metrics calculated
    # ------------------------------------------------------------------------
    def test_tc2_empty_directory(self, project_root, io_structure, tmp_path):
        """TC2: Empty directory -> No metrics calculated.

        Test Case ID: TC2
        Input: "empty_repo" (empty folder)
        Environment description: Empty folder
        Oracle: No metrics are calculated
        """
        empty_repos = tmp_path / "empty_repo"
        empty_repos.mkdir()

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=empty_repos,
            metrics=True,
        )

        assert result.returncode == 0, (
            f"Execution failed with code {result.returncode}\n"
            f"Stderr: {result.stderr}\nStdout: {result.stdout}"
        )

        calculated_metrics = get_metrics_projects(io_structure)

        assert len(calculated_metrics) == 0, (
            f"Expected 0 metrics calculated for empty directory, "
            f"found {len(calculated_metrics)}: {calculated_metrics}"
        )

    # ------------------------------------------------------------------------
    # TC3: Multiple projects without Python files -> MI = 0 and CC = 0
    # ------------------------------------------------------------------------
    def test_tc3_multiple_projects_no_python(
        self, project_root, io_structure, test_repo_dir
    ):
        """TC3: Multiple projects without Python files -> MI = 0 and CC = 0.

        Test Case ID: TC3
        Input: "test_repos/TC3"
        Environment description: Multiple projects without Python files
        Oracle: For all projects, MI = 0 and CC = 0
        """
        test_repos = test_repo_dir / "TC3"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            metrics=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        calculated_metrics = get_metrics_projects(io_structure)

        # Verify that for each project MI = 0 and CC = 0
        for project_name, metrics in calculated_metrics.items():
            ##print(f"[DEBUG] {project_name} -> {metrics}")
            assert metrics["MI_avg"] == 0, (
                f"Project '{project_name}' expected MI_avg = 0, "
                f"got {metrics['MI_avg']}"
            )
            assert metrics["CC_avg"] == 0, (
                f"Project '{project_name}' expected CC_avg = 0, "
                f"got {metrics['CC_avg']}"
            )

    # ------------------------------------------------------------------------
    # TC4: Multiple projects with empty Python files -> MI = 0 and CC = 0
    # ------------------------------------------------------------------------
    def test_tc4_multiple_projects_empty_python(
        self, project_root, io_structure, test_repo_dir
    ):
        """TC4: Multiple projects with empty Python files -> MI = 0 and CC = 0.

        Test Case ID: TC4
        Input: "test_repos/TC4"
        Environment description: Multiple projects with empty Python files
        Oracle: For all projects, MI = 0 and CC = 0
        """
        test_repos = test_repo_dir / "TC4"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            metrics=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        calculated_metrics = get_metrics_projects(io_structure)

        # Verify that there are projects analyzed
        assert (
            len(calculated_metrics) > 0
        ), "Expected at least one project to be analyzed"

        # Verify that for each project MI = 0 and CC = 0
        for project_name, metrics in calculated_metrics.items():
            ##print(f"[DEBUG] {project_name} -> {metrics}")
            assert metrics["MI_avg"] == 0, (
                f"Project '{project_name}' with empty Python files expected MI_avg = 0, "
                f"got {metrics['MI_avg']}"
            )
            assert metrics["CC_avg"] == 0, (
                f"Project '{project_name}' with empty Python files expected CC_avg = 0, "
                f"got {metrics['CC_avg']}"
            )

    # ------------------------------------------------------------------------
    # TC5: Multiple projects with Python files with valid code -> exact MI and CC values
    # ------------------------------------------------------------------------
    def test_tc5_multiple_projects_valid_python(
        self, project_root, io_structure, test_repo_dir
    ):
        """TC5: Multiple projects with Python files with valid code -> exact MI and CC values.

        Test Case ID: TC5
        Input: "test_repos/TC5"
        Environment description: Multiple projects with Python files containing valid code
        Oracle: Exact manually calculated CC_avg and MI_avg values below
        """
        test_repos = test_repo_dir / "TC5"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            metrics=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        calculated_metrics = get_metrics_projects(io_structure)

        # Verify that there are projects analyzed
        assert (
            len(calculated_metrics) > 0
        ), "Expected at least one project to be analyzed"

        # Oracle: Expected exact values calculated manually (see docstring for details)
        expected_metrics = {
            "project1": {
                "CC_avg": 1.67,  # sum([1, 2, 2]) / 3 = 1.6667 -> rounded   # 3 number of blocks
                "MI_avg": 77.51,  # (100.00*2 + 71.89*8) / 10 = 77.512 -> rounded #10 number of lines logic (SLOC)
            },
            "project2": {
                "CC_avg": 1.33,  # sum([1, 1, 2]) / 3 = 1.3333 -> rounded  # 3 number of blocks
                "MI_avg": 88.75,  # (100.00*4 + 79.74*5) / 9 = 88.7444 -> rounded #9 number of lines logic (SLOC)
            },
        }

        # Verify exact values for each project
        for project_name, metrics in calculated_metrics.items():
            # print(f"[DEBUG] {project_name} -> {metrics}")

            if project_name in expected_metrics:
                expected = expected_metrics[project_name]

                assert metrics["CC_avg"] == expected["CC_avg"], (
                    f"Project '{project_name}' expected CC_avg = {expected['CC_avg']}, "
                    f"got {metrics['CC_avg']}"
                )
                assert metrics["MI_avg"] == expected["MI_avg"], (
                    f"Project '{project_name}' expected MI_avg = {expected['MI_avg']}, "
                    f"got {metrics['MI_avg']}"
                )

    # ------------------------------------------------------------------------
    # TC6: Mix of projects -> MI and CC = 0 or > 0 based on content
    # ------------------------------------------------------------------------
    def test_tc6_mixed_projects(self, project_root, io_structure, test_repo_dir):
        """TC6: Mix of projects -> MI and CC = 0 or > 0 based on content.

        Test Case ID: TC6
        Input: "test_repos/TC6"
        Environment description: Multiple projects with a mix of: no Python files,
                                 empty Python files, and Python files with valid code
        Oracle: Exact manually calculated CC_avg and MI_avg values below
        """
        test_repos = test_repo_dir / "TC6"

        if not test_repos.exists():
            pytest.skip(f"Test fixture not found at {test_repos}")

        result = run_main_cli(
            project_root,
            io_path=io_structure,
            repository_path=test_repos,
            metrics=True,
        )

        assert result.returncode == 0, f"Execution failed: {result.stderr}"

        calculated_metrics = get_metrics_projects(io_structure)

        # Verify that there are projects analyzed
        assert (
            len(calculated_metrics) > 0
        ), "Expected at least one project to be analyzed"

        # Oracle: Expected exact values calculated manually (see docstring for details)
        expected_metrics = {
            "project_empty_python_1": {
                "CC_avg": 0,  # Empty python files, default is 0
                "MI_avg": 0,  # Empty python files, default is 0
            },
            "project_empty_python_2": {
                "CC_avg": 0,  # Empty python files, default is 0
                "MI_avg": 0,  # Empty python files, default is 0
            },
            "project_no_python_1": {
                "CC_avg": 0,  # No python files, default is 0
                "MI_avg": 0,  # No python files, default is 0
            },
            "project_no_python": {
                "CC_avg": 0,  # No python files, default is 0
                "MI_avg": 0,  # No python files, default is 0
            },
            "project1": {
                "CC_avg": 1.67,  # sum([1, 2, 2]) / 3 = 1.6667 -> rounded   # 3 number of blocks
                "MI_avg": 77.51,  # (100.00*2 + 71.89*8) / 10 = 77.512 -> rounded #10 number of lines logic (SLOC)
            },
            "project2": {
                "CC_avg": 1.33,  # sum([1, 1, 2]) / 3 = 1.3333 -> rounded  # 3 number of blocks
                "MI_avg": 88.75,  # (100.00*4 + 79.74*5) / 9 = 88.7444 -> rounded #9 number of lines logic (SLOC)
            },
        }

        # Verify exact values for each project
        for project_name, metrics in calculated_metrics.items():
            # print(f"[DEBUG] {project_name} -> {metrics}")

            if project_name in expected_metrics:
                expected = expected_metrics[project_name]

                assert metrics["CC_avg"] == expected["CC_avg"], (
                    f"Project '{project_name}' expected CC_avg = {expected['CC_avg']}, "
                    f"got {metrics['CC_avg']}"
                )
                assert metrics["MI_avg"] == expected["MI_avg"], (
                    f"Project '{project_name}' expected MI_avg = {expected['MI_avg']}, "
                    f"got {metrics['MI_avg']}"
                )
