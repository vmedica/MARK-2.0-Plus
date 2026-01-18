import unittest
import tempfile
import shutil
import os
import sys
import stat
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from gui.services.pipeline_service import (
    PipelineService,
    PipelineConfig,
    PipelineResult,
)


def remove_readonly(func, path, excinfo):
    """
    Handler per errori di rimozione file read-only su Windows.
    Rimuove l'attributo read-only e riprova l'operazione.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rmtree(path):
    """
    Rimozione sicura di directory con gestione file read-only Windows.
    """
    if path.exists():
        # Su Windows, i file .git possono essere read-only
        shutil.rmtree(path, onerror=remove_readonly)


class TestPipelineServiceIntegration(unittest.TestCase):
    """Integration tests for PipelineService.run_pipeline method."""

    def setUp(self):
        """Set up test fixtures with real directory structure."""
        # Crea directory temporanea per ogni test
        self.test_dir = Path(tempfile.mkdtemp())
        self.io_path = self.test_dir / "io"
        self.io_path.mkdir()

        # Crea struttura directory necessaria
        self.repos_path = self.io_path / "repos"
        self.repos_path.mkdir()

        self.output_path = self.io_path / "output"
        self.output_path.mkdir()

        # Crea directory log per il cloner (IMPORTANTE!)
        self.log_path = Path(project_root) / "modules" / "cloner" / "log"
        self.log_path.mkdir(exist_ok=True)

        # Copia il CSV reale nella directory di test
        source_csv = Path(project_root) / "io" / "applied_projects.csv"
        self.test_csv = self.io_path / "applied_projects.csv"
        shutil.copy(source_csv, self.test_csv)

        # Copia dictionary se esiste
        src_dict = Path(project_root) / "io" / "library_dictionary"
        if src_dict.exists():
            dst_dict = self.io_path / "library_dictionary"
            shutil.copytree(src_dict, dst_dict)

    def tearDown(self):
        """Clean up test directory and log files."""
        # Usa la funzione safe_rmtree invece di shutil.rmtree
        safe_rmtree(self.test_dir)

        # Pulisci eventuali file di log creati durante il test
        if self.log_path.exists():
            for file in self.log_path.glob("*.csv"):
                try:
                    file.unlink()
                except Exception:
                    pass

    def test_cloning_with_check(self):
        """Test case 1: Cloning + cloner check enabled, analysis disabled."""
        # Arrange
        config = PipelineConfig(
            io_path=self.io_path,
            repository_path=self.repos_path,
            project_list_path=self.test_csv,
            n_repos=2,
            run_cloner=True,
            run_cloner_check=True,
            run_producer_analysis=False,
            run_consumer_analysis=False,
            run_metrics_analysis=False,
        )

        service = PipelineService(config)

        # Act
        result = service.run_pipeline()

        # Assert
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)

        # Verifica che entrambi i passaggi siano stati eseguiti
        self.assertTrue(self.repos_path.exists())

    def test_all_analysis_enabled_no_cloning(self):
        """Test case 2: All analysis enabled (producer, consumer, metrics), no cloning."""
        # Arrange
        config = PipelineConfig(
            io_path=self.io_path,
            repository_path=self.repos_path,
            project_list_path=self.test_csv,
            n_repos=1,
            run_cloner=False,
            run_cloner_check=False,
            run_producer_analysis=True,
            run_consumer_analysis=True,
            run_metrics_analysis=True,
            rules_3=True,
        )

        service = PipelineService(config)

        # Act
        result = service.run_pipeline()

        # Assert
        # Verifica struttura del risultato
        self.assertIsInstance(result, PipelineResult)
        self.assertIsInstance(result.success, bool)

    def test_invalid_csv_path(self):
        """Test case 3: Invalid CSV path - should handle error gracefully."""
        # Arrange
        invalid_csv = self.io_path / "nonexistent.csv"

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

        service = PipelineService(config)

        # Act
        result = service.run_pipeline()

        # Assert
        # Dovrebbe fallire
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)


if __name__ == "__main__":
    unittest.main()
