import unittest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import sys
import os

# Add project root to path to resolve imports correctly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from gui.services.output_reader import (
    OutputReader,
    OutputTree,
    OutputDirectory,
    OutputFile,
    CSVData,
)


class TestOutputReaderScanOutputTree(unittest.TestCase):
    """Unit tests for OutputReader.scan_output_tree method."""

    def setUp(self):
        """Set up test fixtures."""
        self.output_path = Path("/fake/output")
        self.reader = OutputReader(self.output_path)

    @patch("pathlib.Path.exists")
    def test_scan_output_tree_empty_directory(self, mock_exists):
        """(UT-CR2-04) Test case 1: Empty output directory → returns empty tree."""
        # Arrange
        mock_exists.return_value = False

        # Act
        tree = self.reader.scan_output_tree()

        # Assert
        self.assertIsInstance(tree, OutputTree)
        self.assertEqual(len(tree.producer_dirs), 0)
        self.assertEqual(len(tree.consumer_dirs), 0)
        self.assertEqual(len(tree.metrics_dirs), 0)

    def test_scan_output_tree_with_all_categories(self):
        """(UT-CR2-05)Test case 2: All categories (producer, consumer, metrics) with CSV files."""
        # Arrange
        # Create mock CSV files
        producer_csv1 = Mock(spec=Path)
        producer_csv1.name = "results.csv"

        producer_csv2 = Mock(spec=Path)
        producer_csv2.name = "details.csv"

        consumer_csv = Mock(spec=Path)
        consumer_csv.name = "results.csv"

        metrics_csv = Mock(spec=Path)
        metrics_csv.name = "metrics.csv"

        # Create mock run directories
        producer_run_dir = Mock(spec=Path)
        producer_run_dir.name = "producer_1"
        producer_run_dir.is_dir.return_value = True
        producer_run_dir.glob.return_value = [producer_csv1, producer_csv2]

        consumer_run_dir = Mock(spec=Path)
        consumer_run_dir.name = "consumer_2"
        consumer_run_dir.is_dir.return_value = True
        consumer_run_dir.glob.return_value = [consumer_csv]

        metrics_run_dir = Mock(spec=Path)
        metrics_run_dir.name = "metrics_3"
        metrics_run_dir.is_dir.return_value = True
        metrics_run_dir.glob.return_value = [metrics_csv]

        # Create mock category paths
        producer_path = Mock(spec=Path)
        producer_path.exists.return_value = True
        producer_path.iterdir.return_value = [producer_run_dir]

        consumer_path = Mock(spec=Path)
        consumer_path.exists.return_value = True
        consumer_path.iterdir.return_value = [consumer_run_dir]

        metrics_path = Mock(spec=Path)
        metrics_path.exists.return_value = True
        metrics_path.iterdir.return_value = [metrics_run_dir]

        # Mock the Path division operator to return our mock paths
        with patch.object(Path, "__truediv__") as mock_truediv:

            def side_effect_truediv(other):
                if other == "producer":
                    return producer_path
                elif other == "consumer":
                    return consumer_path
                elif other == "metrics":
                    return metrics_path
                return Mock(spec=Path)

            mock_truediv.side_effect = side_effect_truediv

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


class TestOutputReaderLoadCSV(unittest.TestCase):
    """Unit tests for OutputReader.load_csv method."""

    def setUp(self):
        """Set up test fixtures."""
        self.output_path = Path("/fake/output")
        self.reader = OutputReader(self.output_path)

    @patch("pathlib.Path.exists")
    def test_load_csv_file_not_exists(self, mock_exists):
        """(UT-CR2-06) Test case 3: Non-existent file → raises FileNotFoundError."""
        # Arrange
        csv_file = Path("/fake/missing.csv")
        mock_exists.return_value = False

        # Act & Assert
        with self.assertRaises(FileNotFoundError) as context:
            self.reader.load_csv(csv_file)

        self.assertIn("CSV file not found", str(context.exception))

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="ProjectName,Status,Score\nproject_a,Success,95\nproject_b,Failed,42\nproject_c,Success,88\n",
    )
    @patch("pathlib.Path.exists")
    def test_load_csv_valid_file(self, mock_exists, mock_file):
        """(UT-CR2-07)Test case 4: Valid CSV file → returns CSVData with headers and rows."""
        # Arrange
        csv_file = Path("/fake/test.csv")
        mock_exists.return_value = True

        # Act
        csv_data = self.reader.load_csv(csv_file)

        # Assert
        self.assertIsInstance(csv_data, CSVData)
        self.assertEqual(csv_data.headers, ["ProjectName", "Status", "Score"])
        self.assertEqual(len(csv_data.rows), 3)
        self.assertEqual(csv_data.rows[0], ["project_a", "Success", "95"])
        self.assertEqual(csv_data.rows[1], ["project_b", "Failed", "42"])
        self.assertEqual(csv_data.rows[2], ["project_c", "Success", "88"])
        self.assertEqual(csv_data.row_count, 3)
        self.assertEqual(csv_data.file_path, csv_file)

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("pathlib.Path.exists")
    def test_load_csv_empty_file(self, mock_exists, mock_file):
        """(UT-CR2-08) Test case 5: Empty CSV file → returns empty CSVData."""
        # Arrange
        csv_file = Path("/fake/empty.csv")
        mock_exists.return_value = True

        # Act
        csv_data = self.reader.load_csv(csv_file)

        # Assert
        self.assertEqual(csv_data.headers, [])
        self.assertEqual(csv_data.rows, [])
        self.assertEqual(csv_data.row_count, 0)


class TestOutputReaderFindCompleteAnalyses(unittest.TestCase):
    """Unit tests for OutputReader.find_complete_analyses method."""

    def setUp(self):
        """Set up test fixtures."""
        self.output_path = Path("/fake/output")
        self.reader = OutputReader(self.output_path)

    def test_find_complete_analyses_no_directories(self):
        """(UT-CR3-01) Test case 6: No analysis directories → returns empty list."""
        # Arrange
        producer_path = Mock(spec=Path)
        producer_path.exists.return_value = False

        consumer_path = Mock(spec=Path)
        consumer_path.exists.return_value = False

        metrics_path = Mock(spec=Path)
        metrics_path.exists.return_value = False

        with patch.object(Path, "__truediv__") as mock_truediv:

            def side_effect_truediv(other):
                if other == "producer":
                    return producer_path
                elif other == "consumer":
                    return consumer_path
                elif other == "metrics":
                    return metrics_path
                return Mock(spec=Path)

            mock_truediv.side_effect = side_effect_truediv

            # Act
            analyses = self.reader.find_complete_analyses()

        # Assert
        self.assertEqual(analyses, [])

    def test_find_complete_analyses_all_categories_present(self):
        """(UT-CR3-02) Test case 7: All categories with same analysis ID → returns that ID."""
        # Arrange
        producer_dir = Mock(spec=Path)
        producer_dir.name = "producer_123"
        producer_dir.is_dir.return_value = True

        consumer_dir = Mock(spec=Path)
        consumer_dir.name = "consumer_123"
        consumer_dir.is_dir.return_value = True

        metrics_dir = Mock(spec=Path)
        metrics_dir.name = "metrics_123"
        metrics_dir.is_dir.return_value = True

        producer_path = Mock(spec=Path)
        producer_path.exists.return_value = True
        producer_path.iterdir.return_value = [producer_dir]

        consumer_path = Mock(spec=Path)
        consumer_path.exists.return_value = True
        consumer_path.iterdir.return_value = [consumer_dir]

        metrics_path = Mock(spec=Path)
        metrics_path.exists.return_value = True
        metrics_path.iterdir.return_value = [metrics_dir]

        with patch.object(Path, "__truediv__") as mock_truediv:

            def side_effect_truediv(other):
                if other == "producer":
                    return producer_path
                elif other == "consumer":
                    return consumer_path
                elif other == "metrics":
                    return metrics_path
                return Mock(spec=Path)

            mock_truediv.side_effect = side_effect_truediv

            # Act
            analyses = self.reader.find_complete_analyses()

        # Assert
        self.assertEqual(analyses, ["123"])


if __name__ == "__main__":
    unittest.main()
