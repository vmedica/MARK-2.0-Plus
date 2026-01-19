import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from gui.services.output_reader import OutputReader, CSVData, OutputTree


class TestOutputReaderIntegration(unittest.TestCase):
    """Integration tests for OutputReader main methods."""

    def setUp(self):
        """Set up test fixtures with real directory structure."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.output_path = self.test_dir / "output"
        self.output_path.mkdir()

        self.reader = OutputReader(self.output_path)

    def tearDown(self):
        """Clean up test directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    # === SCAN_OUTPUT_TREE Tests ===

    def test_scan_output_tree_empty_directory(self):
        """TC1: Empty output directory → returns empty tree."""
        # Act
        tree = self.reader.scan_output_tree()

        # Assert
        self.assertIsInstance(tree, OutputTree)
        self.assertEqual(len(tree.producer_dirs), 0)
        self.assertEqual(len(tree.consumer_dirs), 0)
        self.assertEqual(len(tree.metrics_dirs), 0)

    def test_scan_output_tree_with_all_categories(self):
        """TC2: All categories (producer, consumer, metrics) with CSV files."""
        # Arrange - Create complete structure
        # Producer
        producer_dir = self.output_path / "producer" / "producer_1"
        producer_dir.mkdir(parents=True)
        (producer_dir / "results.csv").write_text("ProjectName,Status\nproj1,Yes\n")
        (producer_dir / "details.csv").write_text("Detail1,Detail2\nval1,val2\n")

        # Consumer
        consumer_dir = self.output_path / "consumer" / "consumer_2"
        consumer_dir.mkdir(parents=True)
        (consumer_dir / "results.csv").write_text("ProjectName,Status\nproj2,Yes\n")

        # Metrics
        metrics_dir = self.output_path / "metrics" / "metrics_3"
        metrics_dir.mkdir(parents=True)
        (metrics_dir / "metrics.csv").write_text("ProjectName,CC\nproj3,5.2\n")

        # Act
        tree = self.reader.scan_output_tree()

        # Assert
        self.assertEqual(len(tree.producer_dirs), 1)
        self.assertEqual(len(tree.consumer_dirs), 1)
        self.assertEqual(len(tree.metrics_dirs), 1)

        # Check producer details
        prod_dir = tree.producer_dirs[0]
        self.assertEqual(prod_dir.name, "producer_1")
        self.assertEqual(len(prod_dir.files), 2)
        # Results.csv should be first (is_summary=True)
        self.assertTrue(prod_dir.files[0].is_summary)
        self.assertEqual(prod_dir.files[0].name, "results.csv")

        # Check consumer
        cons_dir = tree.consumer_dirs[0]
        self.assertEqual(cons_dir.name, "consumer_2")
        self.assertEqual(len(cons_dir.files), 1)

        # Check metrics
        metr_dir = tree.metrics_dirs[0]
        self.assertEqual(metr_dir.name, "metrics_3")
        self.assertEqual(len(metr_dir.files), 1)
        self.assertTrue(metr_dir.files[0].is_summary)

    # === LOAD_CSV Tests ===

    def test_load_csv_file_not_exists(self):
        """TC3: Non-existent file → raises FileNotFoundError."""
        # Arrange
        non_existent = self.output_path / "missing.csv"

        # Act & Assert
        with self.assertRaises(FileNotFoundError) as context:
            self.reader.load_csv(non_existent)

        self.assertIn("CSV file not found", str(context.exception))

    def test_load_csv_valid_file(self):
        """TC4: Valid CSV file → returns CSVData with headers and rows."""
        # Arrange
        csv_file = self.output_path / "test.csv"
        csv_file.write_text(
            "ProjectName,Status,Score\n"
            "project_a,Success,95\n"
            "project_b,Failed,42\n"
            "project_c,Success,88\n"
        )

        # Act
        csv_data = self.reader.load_csv(csv_file)

        # Assert
        self.assertIsInstance(csv_data, CSVData)
        self.assertEqual(csv_data.headers, ["ProjectName", "Status", "Score"])
        self.assertEqual(len(csv_data.rows), 3)
        self.assertEqual(csv_data.rows[0], ["project_a", "Success", "95"])
        self.assertEqual(csv_data.rows[1], ["project_b", "Failed", "42"])
        self.assertEqual(csv_data.row_count, 3)
        self.assertEqual(csv_data.file_path, csv_file)

    def test_load_csv_empty_file(self):
        """TC5: Empty CSV file → returns empty CSVData."""
        # Arrange
        csv_file = self.output_path / "empty.csv"
        csv_file.write_text("")

        # Act
        csv_data = self.reader.load_csv(csv_file)

        # Assert
        self.assertEqual(csv_data.headers, [])
        self.assertEqual(csv_data.rows, [])
        self.assertEqual(csv_data.row_count, 0)

    # === FIND_COMPLETE_ANALYSES Tests ===

    def test_find_complete_analyses_no_directories(self):
        """TC6: No analysis directories → returns empty list."""
        # Act
        analyses = self.reader.find_complete_analyses()

        # Assert
        self.assertEqual(analyses, [])

    def test_find_complete_analyses_all_categories_present(self):
        """TC7: All categories with same analysis ID → returns that ID."""
        # Arrange
        (self.output_path / "producer" / "producer_123").mkdir(parents=True)
        (self.output_path / "consumer" / "consumer_123").mkdir(parents=True)
        (self.output_path / "metrics" / "metrics_123").mkdir(parents=True)

        # Act
        analyses = self.reader.find_complete_analyses()

        # Assert
        self.assertEqual(analyses, ["123"])


if __name__ == "__main__":
    unittest.main()
