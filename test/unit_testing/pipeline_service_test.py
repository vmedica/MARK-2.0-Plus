import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from gui.services.pipeline_service import (
    PipelineService,
    PipelineConfig,
    PipelineResult,
)


class TestPipelineServiceUnit(unittest.TestCase):
    """Unit tests for PipelineService.run_pipeline method."""

    def setUp(self):
        """Set up test fixtures with mock configuration."""
        self.io_path = Path("/fake/io")
        self.repos_path = Path("/fake/repos")
        self.csv_path = Path("/fake/projects.csv")

    @patch("gui.services.pipeline_service.RepoInspector")
    @patch("gui.services.pipeline_service.RepoCloner")
    def test_cloning_with_check(self, mock_cloner_class, mock_inspector_class):
        """(UT-CR2-01) Test case 1: Cloning + cloner check enabled, analysis disabled."""
        # Arrange
        config = PipelineConfig(
            io_path=self.io_path,
            repository_path=self.repos_path,
            project_list_path=self.csv_path,
            n_repos=2,
            run_cloner=True,
            run_cloner_check=True,
            run_producer_analysis=False,
            run_consumer_analysis=False,
            run_metrics_analysis=False,
        )

        # Mock instances
        mock_cloner = Mock()
        mock_cloner_class.return_value = mock_cloner

        mock_inspector = Mock()
        mock_inspector_class.return_value = mock_inspector

        service = PipelineService(config)

        # Act
        result = service.run_pipeline()

        # Assert
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)

        # Verify RepoCloner was instantiated correctly
        mock_cloner_class.assert_called_once_with(
            input_path=self.csv_path,
            output_path=self.repos_path,
            n_repos=2,
        )
        mock_cloner.clone_all.assert_called_once()

        # Verify RepoInspector was instantiated correctly
        mock_inspector_class.assert_called_once_with(
            csv_input_path=self.csv_path,
            output_path=self.repos_path,
        )
        mock_inspector.run_analysis.assert_called_once()

        # Verify analysis output dirs are None
        self.assertIsNone(result.producer_output_dir)
        self.assertIsNone(result.consumer_output_dir)
        self.assertIsNone(result.metrics_output_dir)

    @patch("gui.services.pipeline_service.MLAnalysisFacade")
    def test_all_analysis_enabled_no_cloning(self, mock_facade_class):
        """(UT-CR2-02) Test case 2: All analysis enabled (producer, consumer, metrics), no cloning."""
        # Arrange
        config = PipelineConfig(
            io_path=self.io_path,
            repository_path=self.repos_path,
            project_list_path=self.csv_path,
            n_repos=1,
            run_cloner=False,
            run_cloner_check=False,
            run_producer_analysis=True,
            run_consumer_analysis=True,
            run_metrics_analysis=True,
            rules_3=True,
        )

        # Mock facade instances and their return values
        mock_producer_facade = Mock()
        mock_producer_facade.run_analysis.return_value = "producer_123"

        mock_consumer_facade = Mock()
        mock_consumer_facade.run_analysis.return_value = "consumer_456"

        mock_metrics_facade = Mock()
        mock_metrics_facade.run_analysis.return_value = "metrics_789"

        # Configure mock to return different instances for each call
        mock_facade_class.side_effect = [
            mock_producer_facade,
            mock_consumer_facade,
            mock_metrics_facade,
        ]

        service = PipelineService(config)

        # Act
        result = service.run_pipeline()

        # Assert
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)

        # Verify MLAnalysisFacade was called 3 times
        self.assertEqual(mock_facade_class.call_count, 3)

        # Verify producer analysis
        self.assertEqual(result.producer_output_dir, "producer_123")
        mock_producer_facade.run_analysis.assert_called_once()

        # Verify consumer analysis
        self.assertEqual(result.consumer_output_dir, "consumer_456")
        # Consumer should be called with rules_3=True
        mock_consumer_facade.run_analysis.assert_called_once_with(rules_3=True)

        # Verify metrics analysis
        self.assertEqual(result.metrics_output_dir, "metrics_789")
        mock_metrics_facade.run_analysis.assert_called_once()

    @patch("gui.services.pipeline_service.RepoCloner")
    def test_invalid_csv_path(self, mock_cloner_class):
        """(UT-CR2-03) Test case 3: Invalid CSV path - should handle error gracefully."""
        # Arrange
        invalid_csv = Path("/fake/nonexistent.csv")

        config = PipelineConfig(
            io_path=self.io_path,
            repository_path=self.repos_path,
            project_list_path=invalid_csv,
            n_repos=1,
            run_cloner=True,
            run_cloner_check=False,
            run_producer_analysis=False,
            run_consumer_analysis=False,
            run_metrics_analysis=False,
        )

        # Mock cloner to raise an exception
        mock_cloner = Mock()
        mock_cloner.clone_all.side_effect = FileNotFoundError("CSV file not found")
        mock_cloner_class.return_value = mock_cloner

        service = PipelineService(config)

        # Act
        result = service.run_pipeline()

        # Assert
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
        self.assertIn("CSV file not found", result.error_message)

        # Verify cloner was called before failing
        mock_cloner.clone_all.assert_called_once()


if __name__ == "__main__":
    unittest.main()
