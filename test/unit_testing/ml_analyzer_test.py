import unittest
from unittest.mock import Mock, patch, mock_open
import os
import pandas as pd
import sys

# Add project root to path to resolve imports correctly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from modules.analyzer.ml_analyzer import MLAnalyzer
from modules.analyzer.ml_roles import AnalyzerRole


class ConcreteMLAnalyzer(MLAnalyzer):
    """Concrete implementation of MLAnalyzer for testing purposes."""

    def check_library(self, file, **kwargs):
        # Mock implementation that returns values based on test setup
        if hasattr(self, "_mock_check_library"):
            return self._mock_check_library(file, **kwargs)
        return [], [], []


class TestMLAnalyzerAnalyzeSingleFile(unittest.TestCase):
    """Unit tests for MLAnalyzer.analyze_single_file method."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ConcreteMLAnalyzer(
            role=AnalyzerRole.PRODUCER,
            library_dicts=[],
            filters=[],
            keyword_strategy=None,
        )

    def test_analyze_single_file_not_exists(self):
        """(UT-CR1-01) Test case 1: File does not exist."""
        # Arrange
        fake_file = "non_existent_file.py"
        fake_repo = "/fake/repo"

        # Act
        with patch("os.path.isfile", return_value=False):
            result = self.analyzer.analyze_single_file(fake_file, fake_repo)

        # Assert
        libraries, keywords, list_load_keywords, cc_blocks, mi_val, sloc_val = result
        self.assertEqual(libraries, [])
        self.assertEqual(keywords, [])
        self.assertEqual(list_load_keywords, [])
        self.assertEqual(cc_blocks, [])
        self.assertEqual(mi_val, 0)
        self.assertEqual(sloc_val, 0)

    def test_analyze_single_file_read_error(self):      #Command for execute only function and report: coverage run -m pytest test/unit_testing/ml_analyzer_test.py::TestMLAnalyzerAnalyzeSingleFile::test_analyze_single_file_read_error -v; coverage report -m --include="modules/analyzer/ml_analyzer.py"
        """(UT-CR1-02) Test case 2: Error reading file."""
        # Arrange
        fake_file = "existing_file.py"
        fake_repo = "/fake/repo"

        def mock_check_library(file, **kwargs):
            return (
                ["tensorflow"],
                [{"library": "tensorflow", "keyword": "fit", "line_number": 1}],
                [],
            )

        self.analyzer._mock_check_library = mock_check_library

        # Act
        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", side_effect=IOError("Read error")):
                result = self.analyzer.analyze_single_file(fake_file, fake_repo)

        # Assert
        libraries, keywords, list_load_keywords, cc_blocks, mi_val, sloc_val = result
        self.assertEqual(libraries, ["tensorflow"])
        self.assertEqual(len(keywords), 1)
        self.assertEqual(list_load_keywords, [])
        self.assertEqual(cc_blocks, [])
        self.assertEqual(mi_val, 0)
        self.assertEqual(sloc_val, 0)

    @patch("modules.analyzer.ml_analyzer.mi_visit")
    @patch("modules.analyzer.ml_analyzer.cc_visit")
    def test_analyze_single_file_with_exceptions_and_keywords(
        self, mock_cc_visit, mock_mi_visit
    ):
        """(UT-CR1-03) Test case 3: File reads successfully, CC and MI raise exceptions, keywords found."""
        # Arrange
        fake_file = "test_file.py"
        fake_repo = "/fake/repo"
        code_content = "import tensorflow as tf\nmodel.fit(X, y)\nprint('test')"

        def mock_check_library(file, **kwargs):
            return (
                ["tensorflow"],
                [{"library": "tensorflow", "keyword": "fit", "line_number": 2}],
                [],
            )

        self.analyzer._mock_check_library = mock_check_library

        # Mock CC and MI to raise exceptions
        mock_cc_visit.side_effect = Exception("CC calculation error")
        mock_mi_visit.side_effect = Exception("MI calculation error")

        # Act
        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", mock_open(read_data=code_content)):
                result = self.analyzer.analyze_single_file(fake_file, fake_repo)

        # Assert
        libraries, keywords, list_load_keywords, cc_blocks, mi_val, sloc_val = result
        self.assertEqual(libraries, ["tensorflow"])
        self.assertEqual(len(keywords), 1)
        self.assertEqual(keywords[0]["keyword"], "fit")
        self.assertEqual(list_load_keywords, [])
        self.assertEqual(cc_blocks, [])  # Exception handled, returns empty list
        self.assertEqual(mi_val, 0)  # Exception handled, returns 0
        self.assertEqual(sloc_val, 3)  # 3 non-empty, non-comment lines

    @patch("modules.analyzer.ml_analyzer.mi_visit")
    @patch("modules.analyzer.ml_analyzer.cc_visit")
    def test_analyze_single_file_success_no_keywords(
        self, mock_cc_visit, mock_mi_visit
    ):
        """(UT-CR1-04) Test case 4: CC and MI succeed, but no keywords found."""
        # Arrange
        fake_file = "simple_file.py"
        fake_repo = "/fake/repo"
        code_content = "def add(a, b):\n    return a + b\n\nprint(add(1, 2))"

        def mock_check_library(file, **kwargs):
            return [], [], []  # No libraries, no keywords

        self.analyzer._mock_check_library = mock_check_library

        # Mock CC and MI to return valid values
        mock_cc_block = Mock()
        mock_cc_block.complexity = 1
        mock_cc_visit.return_value = [mock_cc_block]
        mock_mi_visit.return_value = 85.5

        # Act
        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", mock_open(read_data=code_content)):
                result = self.analyzer.analyze_single_file(fake_file, fake_repo)

        # Assert
        libraries, keywords, list_load_keywords, cc_blocks, mi_val, sloc_val = result
        self.assertEqual(libraries, [])
        self.assertEqual(keywords, [])
        self.assertEqual(list_load_keywords, [])
        self.assertEqual(len(cc_blocks), 1)
        self.assertEqual(cc_blocks[0].complexity, 1)
        self.assertEqual(mi_val, 85.5)
        self.assertEqual(sloc_val, 3)  # 3 non-empty, non-comment lines


class TestMLAnalyzerAnalyzeProject(unittest.TestCase):
    """Unit tests for MLAnalyzer.analyze_project method."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ConcreteMLAnalyzer(
            role=AnalyzerRole.PRODUCER,
            library_dicts=[],
            filters=[],
            keyword_strategy=None,
        )

    @patch("modules.scanner.project_scanner.ProjectScanner.is_valid_file")
    @patch("os.walk")
    @patch("pandas.DataFrame.to_csv")
    def test_analyze_project_non_metrics_with_keywords(
        self, mock_to_csv, mock_walk, mock_is_valid_file
    ):
        """(UT-CR1-05) Test case 1: Role != METRICS, includes invalid file, valid file without keywords, valid file with keywords."""
        # Arrange
        repo = "/fake/repo"
        project = "test_project"
        directory = "test_dir"
        output_folder = "/fake/output"

        # Mock os.walk to return specific files
        mock_walk.return_value = [
            (
                "/fake/repo",
                [],
                ["invalid_file.txt", "no_keywords.py", "with_keywords.py"],
            )
        ]

        # Mock is_valid_file to return False for invalid_file.txt, True for .py files
        def side_effect_is_valid(filename, filters):
            return filename.endswith(".py")

        mock_is_valid_file.side_effect = side_effect_is_valid

        # Mock analyze_single_file to return different results
        call_count = {"count": 0}

        def mock_analyze_single_file(file, repo, **kwargs):
            call_count["count"] += 1
            if "no_keywords.py" in file:
                # Valid file without keywords
                return [], [], [], [], 85.5, 10
            elif "with_keywords.py" in file:
                # Valid file with keywords
                return (
                    ["tensorflow"],
                    [
                        {"library": "tensorflow", "keyword": "fit", "line_number": 5},
                        {
                            "library": "tensorflow",
                            "keyword": "train",
                            "line_number": 10,
                        },
                    ],
                    [],
                    [],
                    90.0,
                    20,
                )
            return [], [], [], [], 0, 0

        self.analyzer.analyze_single_file = mock_analyze_single_file

        # Act
        df, cc_vals, mi_vals, sloc_vals = self.analyzer.analyze_project(
            repo, project, directory, output_folder
        )

        # Assert
        # Only 2 files should be processed (invalid_file.txt is skipped)
        self.assertEqual(call_count["count"], 2)

        # DataFrame should have 2 rows (2 keywords from with_keywords.py)
        self.assertEqual(len(df), 2)
        self.assertFalse(df.empty)

        # Verify CSV was saved
        mock_to_csv.assert_called_once()

        # Check the actual path passed to to_csv
        actual_csv_path = mock_to_csv.call_args[0][0]
        expected_csv_filename = f"{project}_{directory}_ml_producer.csv"

        # Verify the filename is correct (avoid path separator issues)
        self.assertTrue(actual_csv_path.endswith(expected_csv_filename))
        self.assertIn(output_folder, actual_csv_path)

        # Verify index=False was passed
        self.assertEqual(mock_to_csv.call_args[1]["index"], False)

        # Verify row content
        self.assertEqual(df.iloc[0]["keyword"], "fit")
        self.assertEqual(df.iloc[1]["keyword"], "train")
        self.assertEqual(df.iloc[0]["libraries"], "tensorflow")

        # For non-METRICS role, metrics lists should be empty
        self.assertEqual(cc_vals, [])
        self.assertEqual(mi_vals, [])
        self.assertEqual(sloc_vals, [])

    @patch("modules.scanner.project_scanner.ProjectScanner.is_valid_file")
    @patch("os.walk")
    @patch("pandas.DataFrame.to_csv")
    def test_analyze_project_metrics_role(
        self, mock_to_csv, mock_walk, mock_is_valid_file
    ):
        """(UT-CR1-06) Test case 2: Role == METRICS, includes file with SLOC > 0 and file with SLOC == 0."""
        # Arrange
        metrics_analyzer = ConcreteMLAnalyzer(
            role=AnalyzerRole.METRICS,
            library_dicts=[],
            filters=[],
            keyword_strategy=None,
        )

        repo = "/fake/repo"
        project = "test_project"
        directory = "test_dir"
        output_folder = "/fake/output"

        # Mock os.walk to return specific files
        mock_walk.return_value = [("/fake/repo", [], ["with_sloc.py", "no_sloc.py"])]

        # Mock is_valid_file to return True for all .py files
        mock_is_valid_file.return_value = True

        # Mock analyze_single_file
        def mock_analyze_single_file(file, repo, **kwargs):
            mock_cc_block1 = Mock()
            mock_cc_block1.complexity = 3
            mock_cc_block2 = Mock()
            mock_cc_block2.complexity = 5

            if "with_sloc.py" in file:
                # File with SLOC > 0, no keywords
                return [], [], [], [mock_cc_block1, mock_cc_block2], 85.5, 25
            elif "no_sloc.py" in file:
                # File with SLOC == 0, no keywords
                return [], [], [], [], 0, 0
            return [], [], [], [], 0, 0

        metrics_analyzer.analyze_single_file = mock_analyze_single_file

        # Act
        df, cc_vals, mi_vals, sloc_vals = metrics_analyzer.analyze_project(
            repo, project, directory, output_folder
        )

        # Assert
        # DataFrame should be empty (no keywords found)
        self.assertTrue(df.empty)

        # CSV should not be saved
        mock_to_csv.assert_not_called()

        # Metrics should be collected only for file with SLOC > 0
        self.assertEqual(cc_vals, [3, 5])  # Two CC blocks from with_sloc.py
        self.assertEqual(mi_vals, [(85.5, 25)])  # One MI/SLOC pair
        self.assertEqual(sloc_vals, [25])  # One SLOC value


class TestMLAnalyzerAnalyzeProjectsSet(unittest.TestCase):
    """Unit tests for MLAnalyzer.analyze_projects_set method."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ConcreteMLAnalyzer(
            role=AnalyzerRole.PRODUCER,
            library_dicts=[],
            filters=[],
            keyword_strategy=None,
        )

    @patch("os.path.isdir")
    @patch("os.listdir")
    @patch("pandas.DataFrame.to_csv")
    def test_analyze_projects_set_non_metrics_with_mixed_paths(
        self, mock_to_csv, mock_listdir, mock_isdir
    ):
        """(UT-CR1-07) Test case 1: Role != METRICS with non-dir project, non-dir path, and valid dir returning non-empty df."""
        # Arrange
        input_folder = "/fake/input"
        output_folder = "/fake/output"

        # Mock os.listdir for input folder to return mixed items
        def listdir_side_effect(path):
            if path == input_folder:
                return ["not_a_project.txt", "project_A", "project_B"]
            elif path == os.path.join(input_folder, "project_A"):
                return ["not_a_dir.py", "src", "tests"]
            elif path == os.path.join(input_folder, "project_B"):
                return ["main"]
            return []

        mock_listdir.side_effect = listdir_side_effect

        # Mock os.path.isdir to return appropriate values
        def isdir_side_effect(path):
            # not_a_project.txt is not a dir
            if "not_a_project.txt" in path:
                return False
            # not_a_dir.py is not a dir
            if "not_a_dir.py" in path:
                return False
            # All other paths are directories
            if any(
                x in path for x in ["project_A", "project_B", "src", "tests", "main"]
            ):
                return True
            return False

        mock_isdir.side_effect = isdir_side_effect

        # Mock analyze_project to return non-empty df for valid directories
        call_count = {"count": 0}

        def mock_analyze_project(repo, project, directory, output_folder, **kwargs):
            call_count["count"] += 1

            # Create non-empty DataFrame with keywords
            df = pd.DataFrame(
                [
                    {
                        "ProjectName": f"{project}/{directory}",
                        "Is ML producer": "Yes",
                        "libraries": "sklearn",
                        "where": f"{repo}/train.py",
                        "keyword": "fit",
                        "line_number": 10,
                    }
                ]
            )

            # Return empty metrics for non-METRICS role
            return df, [], [], []

        self.analyzer.analyze_project = mock_analyze_project

        # Act
        result_df = self.analyzer.analyze_projects_set(input_folder, output_folder)

        # Assert
        # Should process only valid directories: project_A/src, project_A/tests, project_B/main
        # (not_a_project.txt and not_a_dir.py are skipped)
        self.assertEqual(call_count["count"], 3)

        # Result DataFrame should not be empty (contains all project results)
        self.assertFalse(result_df.empty)
        self.assertEqual(len(result_df), 3)  # 3 valid directories

        # Verify results.csv was saved
        self.assertEqual(mock_to_csv.call_count, 1)  # Only for results.csv

        # Check results.csv was called
        results_csv_calls = [
            call for call in mock_to_csv.call_args_list if "results.csv" in str(call)
        ]
        self.assertEqual(len(results_csv_calls), 1)

        actual_results_path = results_csv_calls[0][0][0]
        self.assertTrue(actual_results_path.endswith("results.csv"))
        self.assertIn(output_folder, actual_results_path)

    @patch("os.path.isdir")
    @patch("os.listdir")
    @patch("pandas.DataFrame.to_csv")
    def test_analyze_projects_set_metrics_with_empty_and_full_projects(
        self, mock_to_csv, mock_listdir, mock_isdir
    ):
        """(UT-CR1-08) Test case 2: Role == METRICS with project A (empty cc/sloc) and project B (with cc/sloc), all df empty."""
        # Arrange
        metrics_analyzer = ConcreteMLAnalyzer(
            role=AnalyzerRole.METRICS,
            library_dicts=[],
            filters=[],
            keyword_strategy=None,
        )

        input_folder = "/fake/input"
        output_folder = "/fake/output"

        # Mock os.listdir
        def listdir_side_effect(path):
            if path == input_folder:
                return ["project_A", "project_B"]
            elif path == os.path.join(input_folder, "project_A"):
                return ["src"]
            elif path == os.path.join(input_folder, "project_B"):
                return ["main"]
            return []

        mock_listdir.side_effect = listdir_side_effect

        # Mock os.path.isdir - all are valid directories
        mock_isdir.return_value = True

        # Mock analyze_project
        call_count = {"count": 0}

        def mock_analyze_project(repo, project, directory, output_folder, **kwargs):
            call_count["count"] += 1

            # Always return empty DataFrame (no keywords)
            df = pd.DataFrame()

            if "project_A" in project:
                # Project A: empty cc and sloc == 0 (else branches)
                return df, [], [], []
            elif "project_B" in project:
                # Project B: non-empty cc and sloc > 0 (true branches)
                cc_vals = [2, 4, 6]
                mi_vals = [(80.5, 20), (90.0, 30)]
                sloc_vals = [20, 30]
                return df, cc_vals, mi_vals, sloc_vals

            return df, [], [], []

        metrics_analyzer.analyze_project = mock_analyze_project

        # Act
        result_df = metrics_analyzer.analyze_projects_set(input_folder, output_folder)

        # Assert
        # Should process 2 directories
        self.assertEqual(call_count["count"], 2)

        # Result DataFrame should be empty (no keywords found)
        self.assertTrue(result_df.empty)

        # Verify results.csv was NOT saved (df is empty)
        results_csv_calls = [
            call for call in mock_to_csv.call_args_list if "results.csv" in str(call)
        ]
        self.assertEqual(len(results_csv_calls), 0)

        # Verify project_metrics was populated correctly
        self.assertEqual(len(metrics_analyzer.project_metrics), 2)

        # Project A metrics (else branches: cc_avg=0, mi_avg=0)
        project_a_metrics = next(
            m
            for m in metrics_analyzer.project_metrics
            if m["ProjectName"] == "project_A"
        )
        self.assertEqual(project_a_metrics["CC_avg"], 0)
        self.assertEqual(project_a_metrics["MI_avg"], 0)

        # Project B metrics (true branches: calculated averages)
        project_b_metrics = next(
            m
            for m in metrics_analyzer.project_metrics
            if m["ProjectName"] == "project_B"
        )
        # CC_avg = (2 + 4 + 6) / 3 = 4.0
        self.assertEqual(project_b_metrics["CC_avg"], 4.0)
        # MI_avg = (80.5*20 + 90.0*30) / (20+30) = (1610 + 2700) / 50 = 86.2
        self.assertEqual(project_b_metrics["MI_avg"], 86.2)

        # Verify metrics.csv was saved
        metrics_csv_calls = [
            call for call in mock_to_csv.call_args_list if "metrics.csv" in str(call)
        ]
        self.assertEqual(len(metrics_csv_calls), 1)

        actual_metrics_path = metrics_csv_calls[0][0][0]
        self.assertTrue(actual_metrics_path.endswith("metrics.csv"))
        self.assertIn(output_folder, actual_metrics_path)


if __name__ == "__main__":
    unittest.main()
