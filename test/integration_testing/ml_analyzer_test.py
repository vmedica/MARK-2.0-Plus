import unittest
import tempfile
import os
import shutil
import sys
from unittest.mock import patch

# Add project root to path to resolve imports correctly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from modules.analyzer.analyzer_factory import AnalyzerFactory
from modules.analyzer.ml_roles import AnalyzerRole
from modules.analyzer.builder.consumer_analyzer_builder import (
    ConsumerAnalyzerBuilder,
)  # required import
from modules.analyzer.builder.producer_analyzer_builder import (
    ProducerAnalyzerBuilder,
)  # required import
from modules.analyzer.builder.metrics_analyzer_builder import (
    MetricsAnalyzerBuilder,
)  # required import


class TestMLAnalyzerIntegration(unittest.TestCase):
    """Integration tests for MLAnalyzer.analyze_single_file method."""

    def setUp(self):
        """Set up test fixtures with real analyzer instances."""
        # Change working directory to project root
        self.original_cwd = os.getcwd()
        os.chdir(project_root)

        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create real analyzer instances
        self.producer_analyzer = AnalyzerFactory.create_builder(
            AnalyzerRole.PRODUCER
        ).build()

        self.consumer_analyzer = AnalyzerFactory.create_builder(
            AnalyzerRole.CONSUMER
        ).build()

    def tearDown(self):
        """Clean up test directory and restore working directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        # Restore original working directory
        os.chdir(self.original_cwd)

    def test_analyze_single_file_not_exists(self):
        """Test case 1: File does not exist - Integration test."""
        # Arrange
        non_existent_file = os.path.join(self.test_dir, "non_existent.py")
        fake_repo = self.test_dir

        # Act
        result = self.producer_analyzer.analyze_single_file(
            non_existent_file, fake_repo
        )

        # Assert
        libraries, keywords, list_load_keywords, cc_blocks, mi_val, sloc_val = result
        self.assertEqual(libraries, [])
        self.assertEqual(keywords, [])
        self.assertEqual(list_load_keywords, [])
        self.assertEqual(cc_blocks, [])
        self.assertEqual(mi_val, 0)
        self.assertEqual(sloc_val, 0)

    def test_analyze_single_file_read_error(self):
        """Test case 2: Error reading file - Integration test with simulated read error."""
        # Arrange
        test_file = os.path.join(self.test_dir, "unreadable.py")

        # Create file that exists
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("import tensorflow as tf\nmodel.fit(X, y)")

        # Track how many times the file has been opened
        open_count = {"count": 0}
        original_open = open

        def mock_open_with_error(file, *args, **kwargs):
            if os.path.abspath(file) == os.path.abspath(test_file):
                open_count["count"] += 1
                # Allow first two open (for check_library and extract_keywords), fail on third (for metrics)
                if open_count["count"] > 2 and "r" in args:
                    raise PermissionError(f"Permission denied: {file}")
            return original_open(file, *args, **kwargs)

        # Act
        with patch("builtins.open", side_effect=mock_open_with_error):
            result = self.producer_analyzer.analyze_single_file(
                test_file, self.test_dir
            )

        # Assert
        libraries, keywords, list_load_keywords, cc_blocks, mi_val, sloc_val = result

        # check_library is called first and finds ML keywords
        self.assertGreater(len(libraries), 0, "Should detect tensorflow library")

        # But file read fails on second attempt, so metrics should be 0
        self.assertEqual(cc_blocks, [], "CC should be empty due to read error")
        self.assertEqual(mi_val, 0, "MI should be 0 due to read error")
        self.assertEqual(sloc_val, 0, "SLOC should be 0 due to read error")

    def test_analyze_single_file_with_invalid_syntax_and_keywords(self):
        """Test case 3: File with syntax errors (CC/MI exceptions) but valid ML keywords."""
        # Arrange
        test_file = os.path.join(self.test_dir, "invalid_syntax.py")

        # Create file with invalid Python syntax that causes CC/MI to fail
        code_content = """
import tensorflow as tf
from tensorflow import keras

# Invalid syntax that breaks AST parsing
def train_model(
    model.fit(X_train, y_train, epochs=10)
    
# Missing closing parenthesis and proper function definition
model = keras.Sequential()
model.compile(optimizer='adam'
"""

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(code_content)

        # Act
        result = self.producer_analyzer.analyze_single_file(test_file, self.test_dir)

        # Assert
        libraries, keywords, list_load_keywords, cc_blocks, mi_val, sloc_val = result

        # Should find ML libraries and keywords despite syntax errors
        self.assertGreater(len(libraries), 0, "Should detect tensorflow library")
        self.assertGreater(len(keywords), 0, "Should detect training keywords")

        # CC and MI should fail due to syntax errors
        self.assertEqual(cc_blocks, [], "CC should fail on invalid syntax")
        self.assertEqual(mi_val, 0, "MI should fail on invalid syntax")

        # SLOC should still count non-empty, non-comment lines
        self.assertGreater(sloc_val, 0, "Should count source lines")

    def test_analyze_single_file_success_no_keywords(self):
        """Test case 4: Valid Python file without ML keywords - Integration test."""
        # Arrange
        test_file = os.path.join(self.test_dir, "simple_math.py")

        code_content = """
def add(a, b):
    '''Add two numbers.'''
    return a + b

def multiply(a, b):
    '''Multiply two numbers.'''
    result = a * b
    return result

# Main execution
if __name__ == '__main__':
    x = add(5, 3)
    y = multiply(x, 2)
    print(f"Result: {y}")
"""

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(code_content)

        # Act
        result = self.producer_analyzer.analyze_single_file(test_file, self.test_dir)

        # Assert
        libraries, keywords, list_load_keywords, cc_blocks, mi_val, sloc_val = result

        # No ML-related content
        self.assertEqual(libraries, [], "Should not find ML libraries")
        self.assertEqual(keywords, [], "Should not find ML keywords")
        self.assertEqual(list_load_keywords, [], "Should not find load keywords")

        # Valid metrics from radon
        self.assertGreater(len(cc_blocks), 0, "Should calculate CC for functions")
        self.assertGreater(mi_val, 0, "Should calculate positive MI")

        # SLOC should match non-empty, non-comment lines
        expected_sloc = 10  # Approximate count of actual code lines
        self.assertGreaterEqual(
            sloc_val, expected_sloc - 2, "SLOC should be around expected"
        )
        self.assertLessEqual(
            sloc_val, expected_sloc + 2, "SLOC should be around expected"
        )


class TestMLAnalyzerAnalyzeProjectIntegration(unittest.TestCase):
    """Integration tests for MLAnalyzer.analyze_project method."""

    def setUp(self):
        """Set up test fixtures with real analyzer instances."""
        # Change working directory to project root
        self.original_cwd = os.getcwd()
        os.chdir(project_root)

        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

        # Create real analyzer instances
        self.producer_analyzer = AnalyzerFactory.create_builder(
            AnalyzerRole.PRODUCER
        ).build()

        self.metrics_analyzer = AnalyzerFactory.create_builder(
            AnalyzerRole.METRICS
        ).build()

    def tearDown(self):
        """Clean up test directory and restore working directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

        # Restore original working directory
        os.chdir(self.original_cwd)

    def test_analyze_project_non_metrics_with_mixed_files(self):
        """Test case 1: Role != METRICS with invalid file, valid file without keywords, valid file with keywords."""
        # Arrange
        project_name = "test_project"
        directory_name = "src"

        # Create files in test directory
        # 1. Invalid file (not Python)
        invalid_file = os.path.join(self.test_dir, "readme.txt")
        with open(invalid_file, "w", encoding="utf-8") as f:
            f.write("This is a readme file")

        # 2. Valid Python file without ML keywords
        no_keywords_file = os.path.join(self.test_dir, "utils.py")
        with open(no_keywords_file, "w", encoding="utf-8") as f:
            f.write(
                """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

result = add(5, 3)
print(result)
"""
            )

        # 3. Valid Python file with ML keywords
        with_keywords_file = os.path.join(self.test_dir, "train_model.py")
        with open(with_keywords_file, "w", encoding="utf-8") as f:
            f.write(
                """
import tensorflow as tf
from sklearn.ensemble import RandomForestClassifier

# Load data
X_train, y_train = load_data()

# Train model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Evaluate
accuracy = model.score(X_test, y_test)
print(f"Accuracy: {accuracy}")
"""
            )

        # Act
        df, cc_vals, mi_vals, sloc_vals = self.producer_analyzer.analyze_project(
            self.test_dir, project_name, directory_name, self.output_dir
        )

        # Assert
        # DataFrame should contain keywords from with_keywords_file
        self.assertFalse(df.empty, "DataFrame should not be empty")
        self.assertGreater(len(df), 0, "Should have found keywords")

        # Check that CSV file was created
        expected_csv = os.path.join(
            self.output_dir, f"{project_name}_{directory_name}_ml_producer.csv"
        )
        self.assertTrue(os.path.exists(expected_csv), "CSV file should be created")

        # Verify DataFrame content
        self.assertIn(".fit(", df["keyword"].values, "Should find '.fit(' keyword")
        self.assertIn("sklearn", df["libraries"].values, "Should find sklearn library")

        # For non-METRICS role, metrics lists should be empty
        self.assertEqual(cc_vals, [], "CC values should be empty for producer role")
        self.assertEqual(mi_vals, [], "MI values should be empty for producer role")
        self.assertEqual(sloc_vals, [], "SLOC values should be empty for producer role")

        # Verify that invalid file was skipped (only 2 Python files processed)
        project_names = df["ProjectName"].unique()
        self.assertEqual(len(project_names), 1)
        self.assertEqual(project_names[0], f"{project_name}/{directory_name}")

    def test_analyze_project_metrics_role_with_mixed_sloc(self):
        """Test case 2: Role == METRICS with file having SLOC > 0 and file with SLOC == 0."""
        # Arrange
        project_name = "metrics_project"
        directory_name = "code"

        # 1. Valid Python file with SLOC > 0, no ML keywords
        with_sloc_file = os.path.join(self.test_dir, "calculator.py")
        with open(with_sloc_file, "w", encoding="utf-8") as f:
            f.write(
                """
def calculate(a, b, operation):
    if operation == 'add':
        return a + b
    elif operation == 'subtract':
        return a - b
    elif operation == 'multiply':
        return a * b
    elif operation == 'divide':
        if b != 0:
            return a / b
        return None
    return None

result = calculate(10, 5, 'add')
print(result)
"""
            )

        # 2. Empty Python file (SLOC == 0)
        no_sloc_file = os.path.join(self.test_dir, "empty.py")
        with open(no_sloc_file, "w", encoding="utf-8") as f:
            f.write(
                """
# This file only has comments



# And empty lines
"""
            )

        # Act
        df, cc_vals, mi_vals, sloc_vals = self.metrics_analyzer.analyze_project(
            self.test_dir, project_name, directory_name, self.output_dir
        )

        # Assert
        # DataFrame should be empty (no ML keywords found)
        self.assertTrue(df.empty, "DataFrame should be empty (no ML keywords)")

        # CSV should not be created for empty DataFrame
        expected_csv = os.path.join(
            self.output_dir, f"{project_name}_{directory_name}_ml_metrics.csv"
        )
        self.assertFalse(
            os.path.exists(expected_csv), "CSV should not be created for empty results"
        )

        # Metrics should be collected only from file with SLOC > 0
        self.assertGreater(len(cc_vals), 0, "Should have CC values from calculator.py")
        self.assertGreater(len(mi_vals), 0, "Should have MI values from calculator.py")
        self.assertGreater(
            len(sloc_vals), 0, "Should have SLOC values from calculator.py"
        )

        # Verify that MI values are tuples of (mi_value, sloc_value)
        for mi_tuple in mi_vals:
            self.assertIsInstance(mi_tuple, tuple, "MI value should be a tuple")
            self.assertEqual(len(mi_tuple), 2, "MI tuple should have 2 elements")
            mi_value, sloc_value = mi_tuple
            self.assertGreater(mi_value, 0, "MI value should be positive")
            self.assertGreater(sloc_value, 0, "SLOC value should be positive")

        # Verify SLOC values are positive
        for sloc in sloc_vals:
            self.assertGreater(sloc, 0, "SLOC should be greater than 0")

        # Verify CC values are positive
        for cc in cc_vals:
            self.assertGreater(cc, 0, "CC should be greater than 0")


class TestMLAnalyzerAnalyzeProjectsSetIntegration(unittest.TestCase):
    """Integration tests for MLAnalyzer.analyze_projects_set method."""

    def setUp(self):
        """Set up test fixtures with real analyzer instances."""
        # Change working directory to project root
        self.original_cwd = os.getcwd()
        os.chdir(project_root)

        # Create temporary directories for input and output
        self.input_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

        # Create real analyzer instances
        self.producer_analyzer = AnalyzerFactory.create_builder(
            AnalyzerRole.PRODUCER
        ).build()

        self.metrics_analyzer = AnalyzerFactory.create_builder(
            AnalyzerRole.METRICS
        ).build()

    def tearDown(self):
        """Clean up test directories and restore working directory."""
        if os.path.exists(self.input_dir):
            shutil.rmtree(self.input_dir)

        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

        # Restore original working directory
        os.chdir(self.original_cwd)

    def test_analyze_projects_set_non_metrics_with_mixed_paths(self):
        """Test case 1: Role != METRICS with non-dir project, non-dir path, and valid dirs with keywords."""
        # Arrange
        # Create structure:
        # input_dir/
        #   not_a_project.txt (file, not directory - should be skipped)
        #   project_A/
        #     not_a_dir.py (file, not directory - should be skipped)
        #     src/
        #       train.py (with ML keywords)
        #     tests/
        #       test_model.py (with ML keywords)
        #   project_B/
        #     main/
        #       inference.py (with ML keywords)

        # 1. Create not_a_project.txt (should be skipped)
        not_a_project = os.path.join(self.input_dir, "not_a_project.txt")
        with open(not_a_project, "w", encoding="utf-8") as f:
            f.write("This is not a project directory")

        # 2. Create project_A
        project_a_dir = os.path.join(self.input_dir, "project_A")
        os.makedirs(project_a_dir)

        # Create not_a_dir.py in project_A (should be skipped)
        not_a_dir_file = os.path.join(project_a_dir, "not_a_dir.py")
        with open(not_a_dir_file, "w", encoding="utf-8") as f:
            f.write("print('Not a directory')")

        # Create project_A/src with ML code
        src_dir = os.path.join(project_a_dir, "src")
        os.makedirs(src_dir)
        train_file = os.path.join(src_dir, "train.py")
        with open(train_file, "w", encoding="utf-8") as f:
            f.write(
                """
import tensorflow as tf
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier()
model.fit(X_train, y_train)
accuracy = model.score(X_test, y_test)
"""
            )

        # Create project_A/tests with ML code
        tests_dir = os.path.join(project_a_dir, "tests")
        os.makedirs(tests_dir)
        test_file = os.path.join(tests_dir, "test_model.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(
                """
from sklearn.model_selection import cross_val_score

scores = cross_val_score(model, X, y, cv=5)
"""
            )

        # 3. Create project_B/main with ML code
        project_b_dir = os.path.join(self.input_dir, "project_B")
        main_dir = os.path.join(project_b_dir, "main")
        os.makedirs(main_dir)
        inference_file = os.path.join(main_dir, "inference.py")
        with open(inference_file, "w", encoding="utf-8") as f:
            f.write(
                """
import torch

model = torch.load('model.pth')
predictions = model.predict(X_new)
"""
            )

        # Act
        result_df = self.producer_analyzer.analyze_projects_set(
            self.input_dir, self.output_dir
        )

        # Assert
        # Result DataFrame should not be empty
        self.assertFalse(result_df.empty, "Result DataFrame should contain keywords")

        # Should have results from 3 valid directories: project_A/src, project_A/tests, project_B/main
        project_names = result_df["ProjectName"].unique()
        self.assertGreaterEqual(
            len(project_names), 1, "Should have at least 1 project processed"
        )

        # Verify that keywords were found
        self.assertGreater(len(result_df), 0, "Should have found ML keywords")

        # Check that results.csv was created
        results_csv_path = os.path.join(self.output_dir, "results.csv")
        self.assertTrue(
            os.path.exists(results_csv_path), "results.csv should be created"
        )

        # Verify that individual project CSVs were created
        project_csv_files = [
            f for f in os.listdir(self.output_dir) if f.endswith("_ml_producer.csv")
        ]
        self.assertGreater(
            len(project_csv_files), 0, "Should have created project CSV files"
        )

        # Verify that metrics.csv was NOT created (role != METRICS)
        metrics_csv_path = os.path.join(self.output_dir, "metrics.csv")
        self.assertFalse(
            os.path.exists(metrics_csv_path),
            "metrics.csv should not be created for producer role",
        )

        # Verify that ML libraries were detected
        libraries = result_df["libraries"].unique()
        self.assertGreater(len(libraries), 0, "Should have detected ML libraries")

    def test_analyze_projects_set_metrics_with_empty_and_full_projects(self):
        """Test case 2: Role == METRICS with project A (empty cc/sloc) and project B (with cc/sloc), all df empty."""
        # Arrange
        # Create structure:
        # input_dir/
        #   project_A/
        #     src/
        #       empty.py (only comments, SLOC == 0)
        #   project_B/
        #     main/
        #       calculator.py (valid code with SLOC > 0, no ML keywords)

        # 1. Create project_A/src with empty file
        project_a_dir = os.path.join(self.input_dir, "project_A")
        src_a_dir = os.path.join(project_a_dir, "src")
        os.makedirs(src_a_dir)

        empty_file = os.path.join(src_a_dir, "empty.py")
        with open(empty_file, "w", encoding="utf-8") as f:
            f.write(
                """
# This file only contains comments
# No actual code here


# Just more comments
"""
            )

        # 2. Create project_B/main with valid code
        project_b_dir = os.path.join(self.input_dir, "project_B")
        main_b_dir = os.path.join(project_b_dir, "main")
        os.makedirs(main_b_dir)

        calculator_file = os.path.join(main_b_dir, "calculator.py")
        with open(calculator_file, "w", encoding="utf-8") as f:
            f.write(
                """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    result = a * b
    return result

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def complex_calculation(x, y, z):
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x - y
    else:
        if z > 0:
            return x * z
        else:
            return x / z if z != 0 else 0

result = add(10, 5)
print(f"Result: {result}")
"""
            )

        # Act
        result_df = self.metrics_analyzer.analyze_projects_set(
            self.input_dir, self.output_dir
        )

        # Assert
        # Result DataFrame should be empty (no ML keywords)
        self.assertTrue(
            result_df.empty, "Result DataFrame should be empty (no ML keywords)"
        )

        # results.csv should NOT be created (df is empty)
        results_csv_path = os.path.join(self.output_dir, "results.csv")
        self.assertFalse(
            os.path.exists(results_csv_path),
            "results.csv should not be created for empty DataFrame",
        )

        # metrics.csv SHOULD be created (METRICS role)
        metrics_csv_path = os.path.join(self.output_dir, "metrics.csv")
        self.assertTrue(
            os.path.exists(metrics_csv_path), "metrics.csv should be created"
        )

        # Read and verify metrics.csv content
        import pandas as pd

        metrics_df = pd.read_csv(metrics_csv_path)

        # Should have 2 projects
        self.assertEqual(len(metrics_df), 2, "Should have metrics for 2 projects")

        # Project A should have CC_avg=0 and MI_avg=0 (empty cc, sloc == 0)
        project_a_metrics = metrics_df[metrics_df["ProjectName"] == "project_A"]
        self.assertEqual(
            len(project_a_metrics), 1, "Should have one entry for project_A"
        )
        self.assertEqual(
            project_a_metrics.iloc[0]["CC_avg"],
            0,
            "Project A should have CC_avg=0 (else branch)",
        )
        self.assertEqual(
            project_a_metrics.iloc[0]["MI_avg"],
            0,
            "Project A should have MI_avg=0 (else branch)",
        )

        # Project B should have calculated averages (cc non-empty, sloc > 0)
        project_b_metrics = metrics_df[metrics_df["ProjectName"] == "project_B"]
        self.assertEqual(
            len(project_b_metrics), 1, "Should have one entry for project_B"
        )
        self.assertGreater(
            project_b_metrics.iloc[0]["CC_avg"],
            0,
            "Project B should have CC_avg > 0 (true branch)",
        )
        self.assertGreater(
            project_b_metrics.iloc[0]["MI_avg"],
            0,
            "Project B should have MI_avg > 0 (true branch)",
        )

        # Verify that CC values are reasonable
        cc_avg_b = project_b_metrics.iloc[0]["CC_avg"]
        self.assertLess(cc_avg_b, 50, "CC average should be reasonable (< 50)")

        # Verify that MI values are reasonable (0-100 scale)
        mi_avg_b = project_b_metrics.iloc[0]["MI_avg"]
        self.assertGreaterEqual(mi_avg_b, 0, "MI should be >= 0")
        self.assertLessEqual(mi_avg_b, 100, "MI should be <= 100")


if __name__ == "__main__":
    unittest.main()
