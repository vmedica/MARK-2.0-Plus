import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from gui.controller import AppController
from gui.services.output_reader import OutputReader
from gui.services.pipeline_service import PipelineResult


class TestAppControllerIntegration(unittest.TestCase):
    """Integration tests for AppController main methods."""

    def setUp(self):
        """Set up test fixtures with mock main_window and real output_reader."""
        # Create temporary directory structure
        self.test_dir = tempfile.mkdtemp()
        self.io_path = Path(self.test_dir) / "io"
        self.output_path = self.io_path / "output"

        # Create directory structure
        self.io_path.mkdir()
        self.output_path.mkdir()

        # Copy library dictionaries
        src_lib_dict = Path(project_root) / "io" / "library_dictionary"
        dst_lib_dict = self.io_path / "library_dictionary"
        if src_lib_dict.exists():
            shutil.copytree(src_lib_dict, dst_lib_dict)

        # Create real OutputReader
        self.output_reader = OutputReader(self.output_path)

        # Create mock MainWindow
        self.mock_main_window = Mock()
        self.mock_config_view = Mock()
        self.mock_output_view = Mock()
        self.mock_dashboard_view = Mock()

        # Setup view getters
        self.mock_main_window.get_config_view.return_value = self.mock_config_view
        self.mock_main_window.get_output_view.return_value = self.mock_output_view
        self.mock_main_window.get_dashboard_view.return_value = self.mock_dashboard_view

        # Create controller
        self.controller = AppController(
            main_window=self.mock_main_window, output_reader=self.output_reader
        )

    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_on_start_pipeline_invalid_path(self):
        """TC1: Path non esiste → messaggio d'errore."""
        # Arrange
        invalid_path = Path(self.test_dir) / "nonexistent"
        self.mock_config_view.get_config_values.return_value = {
            "io_path": invalid_path,
            "repository_path": Path(self.test_dir) / "repos",
            "project_list_path": Path(self.test_dir) / "projects.csv",
            "n_repos": 10,
            "run_cloner": False,
            "run_cloner_check": False,
            "run_producer_analysis": True,
            "run_consumer_analysis": False,
            "run_metrics_analysis": False,
            "rules_3": True,
        }

        # Act
        self.controller._on_start_pipeline()

        # Assert
        self.mock_main_window.show_error.assert_called_once()
        error_call = self.mock_main_window.show_error.call_args
        self.assertEqual(error_call[0][0], "Invalid Path")
        self.assertIn("does not exist", error_call[0][1])

        # Pipeline should not start
        self.assertIsNone(self.controller._pipeline_service)

    def test_on_start_pipeline_valid_path(self):
        """(IT-CR2-10) TC2: Path esiste → pipeline avviata con thread."""
        # Arrange
        repos_path = self.io_path / "repos"
        repos_path.mkdir()

        project_list = self.io_path / "applied_projects.csv"
        project_list.write_text(
            "project_name,url\ntest_repo,https://github.com/test/repo\n"
        )

        self.mock_config_view.get_config_values.return_value = {
            "io_path": self.io_path,
            "repository_path": repos_path,
            "project_list_path": project_list,
            "n_repos": 1,
            "run_cloner": False,
            "run_cloner_check": False,
            "run_producer_analysis": False,
            "run_consumer_analysis": False,
            "run_metrics_analysis": False,
            "rules_3": True,
        }

        # Act
        with patch.object(self.controller, "_run_pipeline_thread") as mock_run_thread:
            with patch("threading.Thread") as mock_thread_class:
                mock_thread = Mock()
                mock_thread_class.return_value = mock_thread

                self.controller._on_start_pipeline()

                # Assert
                # Output reader path should be updated
                self.assertEqual(
                    self.controller.output_reader.output_path, self.output_path
                )

                # Pipeline service should be created
                self.assertIsNotNone(self.controller._pipeline_service)

                # Config view should enter running state
                self.mock_config_view.set_running_state.assert_called_once_with(True)

                # Thread should be created and started
                mock_thread_class.assert_called_once()
                mock_thread.start.assert_called_once()

    def test_on_pipeline_complete_success(self):
        """(IT-CR2-11) TC3: Pipeline completa con successo → mostra info e aggiorna output."""
        # Arrange
        # Create output structure
        producer_dir = self.output_path / "producer" / "producer_1"
        producer_dir.mkdir(parents=True)
        (producer_dir / "results.csv").write_text(
            "ProjectName,Is ML producer\ntest_proj,Yes\n"
        )

        self.controller._result = PipelineResult(
            success=True,
            producer_output_dir="producer_1",
            consumer_output_dir=None,
            metrics_output_dir=None,
        )

        # Act
        self.controller._on_pipeline_complete()

        # Assert
        # Config view should exit running state
        self.mock_config_view.set_running_state.assert_called_once_with(False)

        # Success message should be shown
        self.mock_main_window.show_info.assert_called_once_with(
            "Success", "Pipeline completed successfully!"
        )

        # Output tree should be refreshed
        self.mock_output_view.populate_tree.assert_called()

        # Should switch to output tab
        self.mock_main_window.switch_to_output_tab.assert_called_once()

    def test_on_pipeline_complete_failure(self):
        """(IT-CR2-12)TC4: Pipeline fallisce → mostra errore."""
        # Arrange
        error_msg = "Analysis failed: invalid configuration"
        self.controller._result = PipelineResult(success=False, error_message=error_msg)

        # Act
        self.controller._on_pipeline_complete()

        # Assert
        # Config view should exit running state
        self.mock_config_view.set_running_state.assert_called_once_with(False)

        # Error message should be shown
        self.mock_main_window.show_error.assert_called_once_with(
            "Pipeline Failed", f"Error: {error_msg}"
        )

        # Should NOT switch to output tab
        self.mock_main_window.switch_to_output_tab.assert_not_called()

    def test_on_pipeline_complete_no_result(self):
        """(IT-CR2-13)TC5: Pipeline completa senza result → errore sconosciuto."""
        # Arrange - no _result attribute set

        # Act
        self.controller._on_pipeline_complete()

        # Assert
        self.mock_config_view.set_running_state.assert_called_once_with(False)
        self.mock_main_window.show_error.assert_called_once_with(
            "Error", "Unknown error occurred"
        )

    def test_refresh_output_tree_success(self):
        """(IT-CR3-03) TC_REFRESH_1: Aggiorna tree con successo quando esistono analisi."""
        # Arrange
        # Create output structure with valid analysis
        producer_dir = self.output_path / "producer" / "producer_123"
        producer_dir.mkdir(parents=True)
        (producer_dir / "results.csv").write_text(
            "ProjectName,Is ML producer\nproject_a,Yes\n"
        )

        consumer_dir = self.output_path / "consumer" / "consumer_123"
        consumer_dir.mkdir(parents=True)
        (consumer_dir / "results.csv").write_text(
            "ProjectName,Is ML consumer\nproject_b,Yes\n"
        )

        # Reset mocks to clear calls from __init__
        self.mock_dashboard_view.populate_analyses.reset_mock()
        self.mock_dashboard_view.show_default_message.reset_mock()
        self.mock_output_view.populate_tree.reset_mock()

        # Act
        self.controller._refresh_output_tree()

        # Assert
        # Dashboard should be populated with analyses
        self.mock_dashboard_view.populate_analyses.assert_called_once()
        analyses = self.mock_dashboard_view.populate_analyses.call_args[0][0]
        self.assertIn("123", analyses)

        # Dashboard should show default message
        self.mock_dashboard_view.show_default_message.assert_called_once()

        # Output view should populate tree
        self.mock_output_view.populate_tree.assert_called_once()
        tree_data = self.mock_output_view.populate_tree.call_args[0][0]
        self.assertIn("producer", tree_data)
        self.assertIn("consumer", tree_data)

    def test_on_file_select_success(self):
        """(IT-CR3-04) TC_FILE_1: Selezione file CSV valido → mostra dati."""
        # Arrange
        csv_file = self.output_path / "test_results.csv"
        csv_file.write_text("ProjectName,Status\nproject1,Success\nproject2,Failed\n")

        # Act
        self.controller._on_file_select(csv_file)

        # Assert
        # Should show loading state
        self.mock_output_view.show_loading.assert_called_once()

        # Should display CSV data
        self.mock_output_view.display_csv_data.assert_called_once()
        call_kwargs = self.mock_output_view.display_csv_data.call_args[1]
        self.assertEqual(call_kwargs["headers"], ["ProjectName", "Status"])
        self.assertEqual(len(call_kwargs["rows"]), 2)
        self.assertEqual(call_kwargs["file_name"], "test_results.csv")

    def test_on_file_select_file_not_found(self):
        """(IT-CR3-05) TC_FILE_2: File non esiste → mostra errore."""
        # Arrange
        nonexistent_file = self.output_path / "nonexistent.csv"

        # Act
        self.controller._on_file_select(nonexistent_file)

        # Assert
        self.mock_output_view.show_loading.assert_called_once()
        self.mock_output_view.show_error.assert_called_once()
        error_msg = self.mock_output_view.show_error.call_args[0][0]
        self.assertIn("not found", error_msg.lower())

    def test_on_analysis_select_with_all_csv_files(self):
        """(IT-CR3-06) TC6: Producer/Consumer/Metrics CSV esistono → calcola metriche complete."""
        # Arrange
        analysis_id = "456"

        # Create producer CSV
        producer_dir = self.output_path / "producer" / f"producer_{analysis_id}"
        producer_dir.mkdir(parents=True)
        (producer_dir / "results.csv").write_text(
            "ProjectName,Is ML producer,libraries,where,keyword,line_number\n"
            "project_a,Yes,tensorflow,main.py,fit,10\n"
            "project_a,Yes,tensorflow,train.py,train,20\n"
        )

        # Create consumer CSV
        consumer_dir = self.output_path / "consumer" / f"consumer_{analysis_id}"
        consumer_dir.mkdir(parents=True)
        (consumer_dir / "results.csv").write_text(
            "ProjectName,Is ML consumer,libraries,where,keyword,line_number\n"
            "project_b,Yes,sklearn,predict.py,predict,15\n"
        )

        # Create metrics CSV
        metrics_dir = self.output_path / "metrics" / f"metrics_{analysis_id}"
        metrics_dir.mkdir(parents=True)
        (metrics_dir / "metrics.csv").write_text(
            "ProjectName,CC_avg,MI_avg\n"
            "project_a,3.5,75.2\n"
            "project_b,4.2,68.8\n"
            "project_c,2.1,82.5\n"
        )

        # Act
        self.controller._on_analysis_select(analysis_id)

        # Assert
        # Summary should be updated
        self.mock_dashboard_view.update_summary.assert_called_once()
        summary = self.mock_dashboard_view.update_summary.call_args[0][0]
        self.assertEqual(summary["Producer"], 1)  # project_a
        self.assertEqual(summary["Consumer"], 1)  # project_b
        self.assertEqual(summary["Producer & Consumer"], 0)  # no overlap

        # Metrics should be calculated
        self.mock_dashboard_view.update_metrics.assert_called_once()
        metrics = self.mock_dashboard_view.update_metrics.call_args[0][0]
        # CC_avg = (3.5 + 4.2 + 2.1) / 3 = 3.27
        self.assertAlmostEqual(metrics["Media Complexity Cyclomatic"], 3.27, places=2)
        # MI_avg = (75.2 + 68.8 + 82.5) / 3 = 75.5
        self.assertAlmostEqual(metrics["Media Maintainability Index"], 75.5, places=2)

        # Keywords should be extracted (top 10)
        self.mock_dashboard_view.update_library.assert_called_once()
        keywords = self.mock_dashboard_view.update_library.call_args[0][0]
        # Should have (library, keyword, count) tuples
        self.assertIsInstance(keywords, list)
        self.assertTrue(all(len(k) == 3 for k in keywords))

    def test_on_analysis_select_csv_not_found(self):
        """(IT-CR3-07) TC7: Producer/Consumer CSV non trovati → metriche a zero."""
        # Arrange
        analysis_id = "999"
        # No CSV files created

        # Act
        self.controller._on_analysis_select(analysis_id)

        # Assert
        # Summary should show zeros
        self.mock_dashboard_view.update_summary.assert_called_once()
        summary = self.mock_dashboard_view.update_summary.call_args[0][0]
        self.assertEqual(summary["Producer"], 0)
        self.assertEqual(summary["Consumer"], 0)
        self.assertEqual(summary["Producer & Consumer"], 0)

        # Metrics should default to zero (FileNotFoundError)
        self.mock_dashboard_view.update_metrics.assert_called_once()
        metrics = self.mock_dashboard_view.update_metrics.call_args[0][0]
        self.assertEqual(metrics["Media Complexity Cyclomatic"], 0)
        self.assertEqual(metrics["Media Maintainability Index"], 0)

        # Keywords should be empty
        self.mock_dashboard_view.update_library.assert_called_once()
        keywords = self.mock_dashboard_view.update_library.call_args[0][0]
        self.assertEqual(len(keywords), 0)


if __name__ == "__main__":
    unittest.main()
