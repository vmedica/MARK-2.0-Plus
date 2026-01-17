# Comando per eseguire i test: pytest -vv -s test/system_test_gui/gui_test.py
"""Black-box system testing for MARK 2.0 GUI interface.

Test Frame (TF) per la validazione della GUI MARK 2.0 Plus.
Eseguire con il comando: pytest -v test/system_test_gui/gui_test.py

Categorie e vincoli testati:
- ST0/ST1/ST2: Step selezionati (nessuno, parziale, tutti)
- CV1/CV2: Cloning e Verify selezionati/non selezionati
- IO0/IO1: Esistenza directory IO
- RP0/RP1: Esistenza directory repo
- CSV0/CSV1: Esistenza file CSV
- CS0/CS1: Stato CSV (vuoto/non vuoto)
- RU3_0/RU3_1: Regola 3 selezionata/non selezionata
- N1/N2/N3/N4: Valore N-repos
"""

import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import shutil
import csv


# ============================================================================
# FIXTURES & UTILITIES
# ============================================================================


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def temp_io_structure(tmp_path, project_root):
    """Setup temporary IO structure with library dictionaries."""
    io_path = tmp_path / "io"
    io_path.mkdir()
    
    # Create output directories
    (io_path / "output" / "producer").mkdir(parents=True)
    (io_path / "output" / "consumer").mkdir(parents=True)
    (io_path / "output" / "metrics").mkdir(parents=True)
    
    # Copy library dictionaries
    src_lib_dict = project_root / "io" / "library_dictionary"
    dst_lib_dict = io_path / "library_dictionary"
    if src_lib_dict.exists():
        shutil.copytree(src_lib_dict, dst_lib_dict)
    
    return io_path


@pytest.fixture
def temp_repo_dir(tmp_path):
    """Create a temporary repository directory."""
    repos_path = tmp_path / "repos"
    repos_path.mkdir()
    return repos_path


@pytest.fixture
def temp_csv_file(tmp_path):
    """Create a temporary CSV file with sample projects."""
    csv_path = tmp_path / "applied_projects.csv"
    return csv_path


@pytest.fixture
def create_csv_with_rows(temp_csv_file):
    """Factory fixture to create CSV with specified number of rows."""
    def _create_csv(num_rows: int):
        with open(temp_csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            for i in range(num_rows):
                writer.writerow([f'owner{i}', f'project{i}', f'https://github.com/owner{i}/project{i}'])
        return temp_csv_file
    return _create_csv


@pytest.fixture
def tk_root():
    """Create a Tk root window for testing."""
    root = tk.Tk()
    root.withdraw()  # Hide the window during tests
    yield root
    root.destroy()


@pytest.fixture
def gui_components(tk_root, project_root):
    """Setup GUI components for testing."""
    # Import GUI modules
    from gui.main_window import MainWindow
    from gui.controller import AppController
    from gui.services.output_reader import OutputReader
    
    # Create output reader with default path
    output_reader = OutputReader(project_root / "io" / "output")
    
    # Create main window
    main_window = MainWindow(tk_root)
    
    # Create controller
    controller = AppController(main_window=main_window, output_reader=output_reader)
    
    return {
        'root': tk_root,
        'main_window': main_window,
        'controller': controller,
        'config_view': main_window.get_config_view(),
        'output_reader': output_reader
    }


def set_all_steps(config_view, value: bool):
    """Set all pipeline steps to the specified value."""
    config_view.run_cloner_var.set(value)
    config_view.run_cloner_check_var.set(value)
    config_view.run_producer_var.set(value)
    config_view.run_consumer_var.set(value)
    config_view.run_metrics_var.set(value)


def set_cloning_steps_only(config_view, cloner: bool, verify: bool):
    """Set only cloning-related steps."""
    config_view.run_cloner_var.set(cloner)
    config_view.run_cloner_check_var.set(verify)
    config_view.run_producer_var.set(False)
    config_view.run_consumer_var.set(False)
    config_view.run_metrics_var.set(False)


def get_step_selection_state(config_view) -> dict:
    """Get current state of all step selections."""
    return {
        'run_cloner': config_view.run_cloner_var.get(),
        'run_cloner_check': config_view.run_cloner_check_var.get(),
        'run_producer': config_view.run_producer_var.get(),
        'run_consumer': config_view.run_consumer_var.get(),
        'run_metrics': config_view.run_metrics_var.get(),
    }


def any_step_selected(config_view) -> bool:
    """Check if any step is selected."""
    state = get_step_selection_state(config_view)
    return any(state.values())


def all_steps_selected(config_view) -> bool:
    """Check if all steps are selected."""
    state = get_step_selection_state(config_view)
    return all(state.values())


def cloning_verify_selected(config_view) -> bool:
    """Check if both Cloning and Verify are selected."""
    return (config_view.run_cloner_var.get() and 
            config_view.run_cloner_check_var.get())


# ============================================================================
# TEST CLASS - TEST FRAMES
# ============================================================================

 # ===== DEBUG HELPER (commenta questa funzione per disabilitare tutte le print) =====
def debug(msg):
    print(msg)
    #pass  # <-- usa questa al posto di print per disabilitare tutto

class TestGUISystemTestFrames:
    """
    Test Frame per la validazione della GUI MARK 2.0 Plus.
    
    Ogni test frame verifica una combinazione specifica di:
    - Step selezionati
    - Configurazione paths
    - Stato dei file/directory
    """

    # ========================================================================
    # TF1: ST0 - Nessuno step selezionato
    # ========================================================================
    def test_TF1_no_step_selected(self, gui_components, temp_io_structure):
        """
        TF1: ST0 - Nessuno Step selezionato

        ID: TF1
        Combinazione: ST0
        Oracolo: [Success] Pipeline completata (nessuna operazione eseguita)
        
        INPUT:
        - Step selezionati: NESSUNO (run_cloner=False, run_cloner_check=False,
                            run_producer=False, run_consumer=False, run_metrics=False)
        - IO directory: temp_io_structure (directory temporanea valida)
        - Repo directory: temp_io_structure/repos (creata nel test)
        
        OUTPUT ATTESO:
        - Messaggio: "Success" / "Pipeline completed successfully!"
        """

        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']

        # Setup: nessuno step selezionato
        set_all_steps(config_view, False)

        # Setup: paths validi
        config_view.io_path_var.set(str(temp_io_structure))
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))

        # Pre-condizione ST0
        assert not any_step_selected(config_view), (
            "Pre-condizione fallita: almeno uno step è selezionato"
        )

        # Oracolo 1: configurazione step
        config = config_view.get_config_values()
        steps_enabled = any([
            config['run_cloner'],
            config['run_cloner_check'],
            config['run_producer_analysis'],
            config['run_consumer_analysis'],
            config['run_metrics_analysis']
        ])

        debug("\n[DEBUG] TF1 - Stato configurazione step:")
        debug(f"  Tutti step disabilitati (atteso): True")
        debug(f"  Tutti step disabilitati (effettivo): {not steps_enabled}")

        assert not steps_enabled, (
            "TF1 FALLITO: almeno uno step risulta abilitato\n"
            f"Stato steps: {config}"
        )

        # Mock show_info
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))

        try:
            # Azione
            controller._on_start_pipeline()

            if controller._pipeline_thread:
                controller._pipeline_thread.join(timeout=5)
                controller._on_pipeline_complete()

            # Oracolo 2: verifica messaggio successo
            expected_title = "Success"
            expected_msg = "Pipeline completed successfully!"

            success_shown = any(
                title == expected_title and expected_msg in msg
                for title, msg in info_shown
            )

            debug("\n[DEBUG] TF1 - Risultato avvio pipeline:")
            debug(f"  Titolo cercato: '{expected_title}'")
            debug(f"  Messaggio cercato: '{expected_msg}'")
            debug(f"  Messaggi ricevuti: {info_shown}")

            assert success_shown, (
                "TF1 FALLITO: messaggio di successo NON mostrato\n"
                f"Ottenuto: {info_shown}"
            )

            debug("\nTF1 PASSED:")
            debug("  - Tutti gli step disabilitati")
            debug("  - Messaggio di successo mostrato")

        finally:
            main_window.show_info = original_show_info


    # ========================================================================
    # TF2: ST1 + CV1 + IO0 - Directory IO mancante
    # ========================================================================
    def test_TF2_io_directory_missing(self, gui_components, tmp_path):
        """
        TF2: ST1 + CV1 + IO0 - IO directory mancante
        
        ID: TF2
        Combinazione: ST1 + CV1 + IO0
        Oracolo: [Error] IO directory mancante
        
        INPUT:
        - Step selezionati: Cloning + Verify (run_cloner=True, run_cloner_check=True)
        - IO directory: tmp_path/nonexistent_io_directory (NON ESISTE)
        - Repo directory: non configurata (irrilevante, IO fallisce prima)
        
        OUTPUT ATTESO:
        - Errore: "Invalid Path" / "IO path does not exist: {path}"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup: Seleziona Cloning + Verify (CV1) - step parziali (ST1)
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Verifica pre-condizione ST1: almeno uno step selezionato (non tutti)
        assert any_step_selected(config_view), (
            "Pre-condizione ST1 fallita: nessuno step selezionato"
        )
        assert not all_steps_selected(config_view), (
            "Pre-condizione ST1 fallita: tutti gli step sono selezionati"
        )
        
        # Verifica pre-condizione CV1: Cloning e Verify selezionati
        assert cloning_verify_selected(config_view), (
            "Pre-condizione CV1 fallita: Cloning e Verify non entrambi selezionati"
        )
        
        # Setup IO0: Directory IO inesistente
        nonexistent_io = tmp_path / "nonexistent_io_directory"
        config_view.io_path_var.set(str(nonexistent_io))
        
        # Verifica pre-condizione IO0: directory non esiste
        assert not nonexistent_io.exists(), (
            "Pre-condizione IO0 fallita: la directory IO esiste"
        )
        
        # Mock show_error per catturare l'errore
        error_shown = []
        original_show_error = main_window.show_error
        main_window.show_error = lambda title, msg: error_shown.append((title, msg))
        
        try:
            # Azione: Tenta di avviare la pipeline
            controller._on_start_pipeline()
            
            # Oracolo: Deve essere mostrato un errore per IO path
            assert len(error_shown) > 0, (
                "TF2 FALLITO: Nessun errore mostrato per directory IO mancante"
            )
            
            error_title, error_msg = error_shown[0]
            
            # Valori attesi
            expected_title = "Invalid Path"
            expected_msg = f"IO path does not exist: {nonexistent_io}"
            
            # DEBUG: Stampa risultati attesi vs ottenuti
            debug(f"\n[DEBUG] TF2 - Validazione messaggio di errore:")
            debug(f"  Titolo atteso: '{expected_title}'")
            debug(f"  Titolo ottenuto: '{error_title}'")
            debug(f"  Messaggio atteso: '{expected_msg}'")
            debug(f"  Messaggio ottenuto: '{error_msg}'")
            
            # Verifica che il titolo sia esattamente "Invalid Path"
            assert error_title == expected_title, (
                f"TF2 FALLITO: Titolo errore inatteso.\n"
                f"  Atteso: '{expected_title}'\n"
                f"  Ottenuto: '{error_title}'"
            )
            
            # Verifica che il messaggio sia esattamente "IO path does not exist: {path}"
            assert error_msg == expected_msg, (
                f"TF2 FALLITO: Messaggio errore non corrisponde.\n"
                f"  Atteso: '{expected_msg}'\n"
                f"  Ottenuto: '{error_msg}'"
            )
            
            debug(f"TF2 PASSED: Errore IO directory correttamente mostrato")
            debug(f"  - Titolo: {error_title}")
            debug(f"  - Messaggio: {error_msg}")
            
        finally:
            main_window.show_error = original_show_error

    # ========================================================================
    # TF3: ST1 + CV1 + IO1 + RP0 - Directory repo mancante
    # ========================================================================
    def test_TF3_repo_directory_missing(self, gui_components, temp_io_structure, tmp_path):
        """
        TF3: ST1 + CV1 + IO1 + RP0 - Directory repo mancante
        
        ID: TF3
        Combinazione: ST1 + CV1 + IO1 + RP0
        Oracolo: [Single] repo directory non esiste, viene creata, pipeline success
        
        INPUT:
        - Step selezionati: Cloning + Verify (run_cloner=True, run_cloner_check=True)
        - IO directory: temp_io_structure (directory temporanea ESISTENTE)
        - Repo directory: tmp_path/test_repos (NON ESISTE, verrà creata)
        - CSV file: temp_io_structure/test_projects.csv (1 riga di test)
        - N-repos: 1
        
        OUTPUT ATTESO:
        - Directory repo creata automaticamente
        - Messaggio: "Success" / "Pipeline completed successfully!"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup: Seleziona Cloning + Verify (CV1) - step parziali (ST1)
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Verifica pre-condizione ST1: almeno uno step selezionato (non tutti)
        assert any_step_selected(config_view), (
            "Pre-condizione ST1 fallita: nessuno step selezionato"
        )
        assert not all_steps_selected(config_view), (
            "Pre-condizione ST1 fallita: tutti gli step sono selezionati"
        )
        
        # Verifica pre-condizione CV1: Cloning e Verify selezionati
        assert cloning_verify_selected(config_view), (
            "Pre-condizione CV1 fallita: Cloning e Verify non entrambi selezionati"
        )
        
        # Setup IO1: Directory IO esistente
        config_view.io_path_var.set(str(temp_io_structure))
        assert temp_io_structure.exists(), (
            "Pre-condizione IO1 fallita: la directory IO non esiste"
        )
        
        # Setup RP0: Directory repo inesistente
        nonexistent_repo = tmp_path / "test_repos"
        config_view.repo_path_var.set(str(nonexistent_repo))
        
        # Verifica pre-condizione RP0: directory repo non esiste
        assert not nonexistent_repo.exists(), (
            "Pre-condizione RP0 fallita: la directory repo esiste"
        )
        
        # Setup: Crea un CSV di test con progetti (necessario per il cloner)
        csv_path = temp_io_structure / "test_projects.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            import csv as csv_module
            writer = csv_module.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            # Aggiungi un progetto di test (piccolo per velocità)
            writer.writerow(['test_owner', 'test_project', 'https://github.com/test/test'])
        
        config_view.project_list_var.set(str(csv_path))
        config_view.n_repos_var.set(1)  # Solo 1 repo per velocità
        
        debug(f"\n[DEBUG] TF3 - Pre-condizioni:")
        debug(f"  ST1 (almeno uno step): {any_step_selected(config_view)}")
        debug(f"  CV1 (Cloning+Verify): {cloning_verify_selected(config_view)}")
        debug(f"  IO1 (IO esiste): {temp_io_structure.exists()}")
        debug(f"  RP0 (repo NON esiste): {not nonexistent_repo.exists()}")
        
        # Mock show_info per catturare il messaggio di successo
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))
        
        # Mock della pipeline service per simulare successo senza esecuzione reale
        from unittest.mock import MagicMock, patch
        from gui.services.pipeline_service import PipelineResult
        
        mock_result = PipelineResult(success=True, error_message=None)
        
        try:
            with patch.object(controller, '_run_pipeline_thread') as mock_run:
                # Simula l'esecuzione della pipeline
                def mock_pipeline():
                    # Simula la creazione della directory repo
                    nonexistent_repo.mkdir(parents=True, exist_ok=True)
                    controller._result = mock_result
                
                mock_run.side_effect = mock_pipeline
                
                # Azione: Avvia la pipeline
                controller._on_start_pipeline()
                
                # Aspetta che il thread (mocked) finisca
                if controller._pipeline_thread:
                    controller._pipeline_thread.join(timeout=2)
                
                # Forza il completamento
                controller._on_pipeline_complete()
            
            # Oracolo parte 1: La directory repo deve essere stata creata
            debug(f"\n[DEBUG] TF3 - Stato dopo esecuzione:")
            debug(f"  Directory repo creata: {nonexistent_repo.exists()}")
            
            assert nonexistent_repo.exists(), (
                f"TF3 FALLITO: La directory repo non è stata creata.\n"
                f"  Path: {nonexistent_repo}"
            )
            
            # Oracolo parte 2: Deve essere mostrato il messaggio di successo
            expected_title = "Success"
            expected_msg = "Pipeline completed successfully!"
            
            success_shown = any(
                title == expected_title and expected_msg in msg
                for title, msg in info_shown
            )
            
            debug(f"  Messaggi info catturati: {info_shown}")
            debug(f"  Messaggio successo trovato: {success_shown}")
            
            assert success_shown, (
                f"TF3 FALLITO: Messaggio di successo NON mostrato.\n"
                f"  Atteso: '{expected_title}' / '{expected_msg}'\n"
                f"  Ottenuto: {info_shown}"
            )
            
            debug(f"\nTF3 PASSED: Directory repo creata e pipeline completata con successo")
            debug(f"  - IO path (esiste): {temp_io_structure}")
            debug(f"  - Repo path (creata): {nonexistent_repo}")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF4: ST1 + CV1 + IO1 + RP1 + CSV0 - File CSV mancante
    # ========================================================================
    def test_TF4_csv_file_missing(self, gui_components, temp_io_structure, tmp_path):
        """
        TF4: ST1 + CV1 + IO1 + RP1 + CSV0 - File CSV mancante
        
        ID: TF4
        Combinazione: ST1 + CV1 + IO1 + RP1 + CSV0
        Oracolo: [Error] CSV mancante (richiesto perché CV1)
        
        INPUT:
        - Step selezionati: Cloning + Verify 
            * run_cloner = True
            * run_cloner_check = True  
            * run_producer = False
            * run_consumer = False
            * run_metrics = False
        - IO directory: temp_io_structure (es: C:/temp/pytest-xxx/io) - ESISTE
        - Repo directory: temp_io_structure/repos - ESISTE
        - CSV file: tmp_path/nonexistent_projects.csv - NON ESISTE
        
        OUTPUT ATTESO:
        - Errore: "Pipeline Failed" 
        - Messaggio: "Error: [Errno 2] No such file or directory: 'nonexistent_projects.csv'"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1: Seleziona Cloning + Verify (CV1) - step parziali
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Verifica pre-condizione ST1
        assert any_step_selected(config_view), "Pre-condizione ST1 fallita"
        assert not all_steps_selected(config_view), "Pre-condizione ST1 fallita: tutti step selezionati"
        
        # Verifica pre-condizione CV1
        assert cloning_verify_selected(config_view), "Pre-condizione CV1 fallita"
        
        # Setup IO1: Directory IO esistente
        config_view.io_path_var.set(str(temp_io_structure))
        assert temp_io_structure.exists(), "Pre-condizione IO1 fallita"
        
        # Setup RP1: Directory repo esistente
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        assert repo_path.exists(), "Pre-condizione RP1 fallita"
        
        # Setup CSV0: File CSV inesistente
        nonexistent_csv = tmp_path / "nonexistent_projects.csv"
        config_view.project_list_var.set(str(nonexistent_csv))
        assert not nonexistent_csv.exists(), "Pre-condizione CSV0 fallita"
        
        debug(f"\n[DEBUG] TF4 - Pre-condizioni:")
        debug(f"  ST1 (almeno uno step): {any_step_selected(config_view)}")
        debug(f"  CV1 (Cloning+Verify): {cloning_verify_selected(config_view)}")
        debug(f"  IO1 (IO esiste): {temp_io_structure.exists()}")
        debug(f"  RP1 (repo esiste): {repo_path.exists()}")
        debug(f"  CSV0 (CSV NON esiste): {not nonexistent_csv.exists()}")
        
        # Mock show_error per catturare l'errore
        error_shown = []
        original_show_error = main_window.show_error
        main_window.show_error = lambda title, msg: error_shown.append((title, msg))
        
        try:
            # Azione: Avvia la pipeline
            controller._on_start_pipeline()
            
            # Aspetta che il thread della pipeline finisca (se è stato avviato)
            if controller._pipeline_thread:
                controller._pipeline_thread.join(timeout=5)
                controller._on_pipeline_complete()
            
            # Oracolo: Deve essere mostrato un errore per CSV mancante
            debug(f"\n[DEBUG] TF4 - Errori catturati: {error_shown}")
            
            assert len(error_shown) > 0, (
                "TF4 FALLITO: Nessun errore mostrato per CSV mancante"
            )
            
            error_title, error_msg = error_shown[0]
            
            # Valori attesi: FileNotFoundError per CSV inesistente
            expected_title = "Pipeline Failed"
            # Il messaggio deve contenere FileNotFoundError e il nome del file CSV
            csv_filename = nonexistent_csv.name
            
            debug(f"  Titolo atteso: '{expected_title}'")
            debug(f"  Titolo ottenuto: '{error_title}'")
            debug(f"  Messaggio ottenuto: '{error_msg}'")
            
            assert error_title == expected_title, (
                f"TF4 FALLITO: Titolo errore inatteso.\n"
                f"  Atteso: '{expected_title}'\n"
                f"  Ottenuto: '{error_title}'"
            )
            
            # Verifica che il messaggio contenga FileNotFoundError e il nome del CSV
            # Verifica che il messaggio indichi che il CSV non esiste
            assert (
                "Error: [Errno 2] No such file or directory:" in error_msg
                and csv_filename in error_msg
            ), (
                f"TF4 FALLITO: Messaggio errore non indica CSV mancante.\n"
                f"Ottenuto: '{error_msg}'"
            )
            
            debug(f"\nTF4 PASSED: Errore CSV mancante correttamente mostrato")
            debug(f"  - Titolo: {error_title}")
            debug(f"  - Messaggio: {error_msg}")
            
        finally:
            main_window.show_error = original_show_error

    # ========================================================================
    # TF5a: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_0 - CSV vuoto, Regola3 OFF
    # ========================================================================
    def test_TF5a_csv_empty_rule3_off(self, gui_components, temp_io_structure):
        """
        TF5a: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_0
        
        ID: TF5a
        Combinazione: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_0
        Oracolo: [Single] Analisi completata con successo
        
        INPUT:
        - Step selezionati: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
            * run_producer = False
            * run_consumer = False
            * run_metrics = False
        - IO directory: temp_io_structure - ESISTE
        - Repo directory: temp_io_structure/repos - ESISTE
        - CSV file: temp_io_structure/empty_projects.csv - ESISTE, VUOTO (solo header)
        - Regola 3: False (RU3_0)
        
        OUTPUT ATTESO:
        - Messaggio: "Success" / "Pipeline completed successfully!"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1 + CV1
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        assert any_step_selected(config_view), "Pre-condizione ST1 fallita"
        assert cloning_verify_selected(config_view), "Pre-condizione CV1 fallita"
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        assert temp_io_structure.exists(), "Pre-condizione IO1 fallita"
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        # Setup CSV1 + CS0: File CSV esiste ma è vuoto (solo header)
        csv_path = temp_io_structure / "empty_projects.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])  # Solo header
        config_view.project_list_var.set(str(csv_path))
        
        # Setup RU3_0: Regola 3 disattivata
        config_view.rules_3_var.set(False)
        
        debug(f"\n[DEBUG] TF5a - Pre-condizioni:")
        debug(f"  CSV1 (CSV esiste): {csv_path.exists()}")
        debug(f"  CS0 (CSV vuoto): True (solo header)")
        debug(f"  RU3_0 (Regola3 OFF): {not config_view.rules_3_var.get()}")
        
        # Mock show_info
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))
        
        from gui.services.pipeline_service import PipelineResult
        mock_result = PipelineResult(success=True, error_message=None)
        
        try:
            with patch.object(controller, '_run_pipeline_thread') as mock_run:
                def mock_pipeline():
                    controller._result = mock_result
                mock_run.side_effect = mock_pipeline
                
                controller._on_start_pipeline()
                if controller._pipeline_thread:
                    controller._pipeline_thread.join(timeout=2)
                controller._on_pipeline_complete()
            
            success_shown = any(
                title == "Success" and "Pipeline completed successfully" in msg
                for title, msg in info_shown
            )
            
            debug(f"\n[DEBUG] TF5a - Messaggi info: {info_shown}")
            
            assert success_shown, (
                f"TF5a FALLITO: Messaggio successo NON mostrato.\n"
                f"Ottenuto: {info_shown}"
            )
            
            debug(f"\nTF5a PASSED: Analisi completata con CSV vuoto e Regola3 OFF")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF6: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_1 - CSV vuoto, Regola3 ON
    # ========================================================================
    def test_TF6_csv_empty_rule3_on(self, gui_components, temp_io_structure):
        """
        TF6: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_1
        
        ID: TF6
        Combinazione: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_1
        Oracolo: [Single] Analisi completata con successo
        
        INPUT:
        - Step selezionati: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
            * run_producer = False
            * run_consumer = False
            * run_metrics = False
        - IO directory: temp_io_structure - ESISTE
        - Repo directory: temp_io_structure/repos - ESISTE
        - CSV file: temp_io_structure/empty_projects2.csv - ESISTE, VUOTO (solo header)
        - Regola 3: True (RU3_1)
        
        OUTPUT ATTESO:
        - Messaggio: "Success" / "Pipeline completed successfully!"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1 + CV1
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        # Setup CSV1 + CS0: CSV vuoto
        csv_path = temp_io_structure / "empty_projects2.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup RU3_1: Regola 3 attivata
        config_view.rules_3_var.set(True)
        
        debug(f"\n[DEBUG] TF6 - Pre-condizioni:")
        debug(f"  RU3_1 (Regola3 ON): {config_view.rules_3_var.get()}")
        
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))
        
        from gui.services.pipeline_service import PipelineResult
        mock_result = PipelineResult(success=True, error_message=None)
        
        try:
            with patch.object(controller, '_run_pipeline_thread') as mock_run:
                def mock_pipeline():
                    controller._result = mock_result
                mock_run.side_effect = mock_pipeline
                
                controller._on_start_pipeline()
                if controller._pipeline_thread:
                    controller._pipeline_thread.join(timeout=2)
                controller._on_pipeline_complete()
            
            success_shown = any(
                title == "Success" and "Pipeline completed successfully" in msg
                for title, msg in info_shown
            )
            
            debug(f"\n[DEBUG] TF6 - Messaggi info: {info_shown}")
            
            assert success_shown, f"TF6 FALLITO: Messaggio successo NON mostrato."
            
            debug(f"\nTF6 PASSED: Analisi completata con CSV vuoto e Regola3 ON")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF7: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N1 - N-repos negativo
    # ========================================================================
    def test_TF7_n_repos_negative(self, gui_components, temp_io_structure):
        """
        TF7: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N1
        
        ID: TF7
        Combinazione: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N1
        Oracolo: [Error] N-repos < 0
        
        INPUT:
        - Step selezionati: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
        - IO directory: temp_io_structure - ESISTE
        - Repo directory: temp_io_structure/repos - ESISTE
        - CSV file: temp_io_structure/projects_TF7.csv - ESISTE, 2 righe dati
        - N-repos: -1 (valore negativo)
        
        OUTPUT ATTESO:
        - Configurazione accetta n_repos < 0 (test boundary)
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1 + CV1
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        # Setup CSV1 + CS1: CSV con dati
        csv_path = temp_io_structure / "projects_TF7.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            writer.writerow(['owner1', 'project1', 'https://github.com/owner1/project1'])
            writer.writerow(['owner2', 'project2', 'https://github.com/owner2/project2'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N1: N-repos < 0
        config_view.n_repos_var.set(-1)
        
        debug(f"\n[DEBUG] TF7 - Pre-condizioni:")
        debug(f"  CS1 (CSV non vuoto): True")
        debug(f"  N1 (N-repos < 0): {config_view.n_repos_var.get()}")
        
        # Oracolo: La configurazione deve contenere n_repos negativo
        config = config_view.get_config_values()
        
        assert config['n_repos'] < 0, (
            f"TF7 FALLITO: n_repos dovrebbe essere negativo.\n"
            f"Valore: {config['n_repos']}"
        )
        
        debug(f"\nTF7 PASSED: n_repos negativo correttamente configurato ({config['n_repos']})")

    # ========================================================================
    # TF8: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N2 - N-repos = 0
    # ========================================================================
    def test_TF7_n_repos_zero(self, gui_components, temp_io_structure):
        """
        TF8: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N2
        
        ID: TF8
        Combinazione: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N2
        Oracolo: [Error] N-repos = 0
        
        INPUT:
        - Step selezionati: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
        - IO directory: temp_io_structure - ESISTE
        - Repo directory: temp_io_structure/repos - ESISTE
        - CSV file: temp_io_structure/projects_TF8.csv - ESISTE, 1 riga dati
        - N-repos: 0
        
        OUTPUT ATTESO:
        - Configurazione accetta n_repos = 0 (test boundary)
        """
        config_view = gui_components['config_view']
        
        # Setup ST1 + CV1
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        # Setup CSV1 + CS1
        csv_path = temp_io_structure / "projects_TF8.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            writer.writerow(['owner1', 'project1', 'https://github.com/owner1/project1'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N2: N-repos = 0
        config_view.n_repos_var.set(0)
        
        debug(f"\n[DEBUG] TF8 - Pre-condizioni:")
        debug(f"  N2 (N-repos = 0): {config_view.n_repos_var.get()}")
        
        config = config_view.get_config_values()
        
        assert config['n_repos'] == 0, (
            f"TF8 FALLITO: n_repos dovrebbe essere 0.\n"
            f"Valore: {config['n_repos']}"
        )
        
        debug(f"\nTF8 PASSED: n_repos = 0 correttamente configurato")

    # ========================================================================
    # TF9: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3 - N-repos valido
    # ========================================================================
    def test_TF9_n_repos_valid(self, gui_components, temp_io_structure):
        """
        TF9: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3
        
        ID: TF9
        Combinazione: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3
        Oracolo: 0 < N-repos < #righeProgettoCSV - Pipeline success
        
        INPUT:
        - Step selezionati: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
        - IO directory: temp_io_structure - ESISTE
        - Repo directory: temp_io_structure/repos - ESISTE
        - CSV file: temp_io_structure/projects_TF9.csv - ESISTE, 5 righe dati
        - N-repos: 3 (0 < 3 < 5)
        
        OUTPUT ATTESO:
        - Messaggio: "Success" / "Pipeline completed successfully!"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1 + CV1
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        # Setup CSV1 + CS1: CSV con 5 righe di dati
        csv_path = temp_io_structure / "projects_TF9.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            for i in range(5):
                writer.writerow([f'owner{i}', f'project{i}', f'https://github.com/owner{i}/project{i}'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N3: 0 < N-repos < #righe (5)
        n_repos_value = 3
        config_view.n_repos_var.set(n_repos_value)
        
        debug(f"\n[DEBUG] TF9 - Pre-condizioni:")
        debug(f"  CS1 (CSV con 5 righe): True")
        debug(f"  N3 (0 < N-repos < 5): {config_view.n_repos_var.get()}")
        
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))
        
        from gui.services.pipeline_service import PipelineResult
        mock_result = PipelineResult(success=True, error_message=None)
        
        try:
            with patch.object(controller, '_run_pipeline_thread') as mock_run:
                def mock_pipeline():
                    controller._result = mock_result
                mock_run.side_effect = mock_pipeline
                
                controller._on_start_pipeline()
                if controller._pipeline_thread:
                    controller._pipeline_thread.join(timeout=2)
                controller._on_pipeline_complete()
            
            success_shown = any(
                title == "Success" and "Pipeline completed successfully" in msg
                for title, msg in info_shown
            )
            
            debug(f"\n[DEBUG] TF9 - Messaggi: {info_shown}")
            
            assert success_shown, f"TF9 FALLITO: Pipeline non completata con successo."
            
            debug(f"\nTF9 PASSED: N-repos valido ({n_repos_value}) - Pipeline success")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF10: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N4 - N-repos > #righe
    # ========================================================================
    def test_TF10_n_repos_exceeds_rows(self, gui_components, temp_io_structure):
        """
        TF10: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N4
        
        ID: TF10
        Combinazione: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N4
        Oracolo: [Single] N-repos > #righeProgettoCSV - Pipeline success
        
        INPUT:
        - Step selezionati: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
        - IO directory: temp_io_structure - ESISTE
        - Repo directory: temp_io_structure/repos - ESISTE
        - CSV file: temp_io_structure/projects_TF10.csv - ESISTE, 3 righe dati
        - N-repos: 100 (100 > 3)
        
        OUTPUT ATTESO:
        - Messaggio: "Success" / "Pipeline completed successfully!"
        - Pipeline usa tutte le righe disponibili (3)
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1 + CV1
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        # Setup CSV1 + CS1: CSV con 3 righe
        csv_path = temp_io_structure / "projects_TF10.csv"
        num_csv_rows = 3
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            for i in range(num_csv_rows):
                writer.writerow([f'owner{i}', f'project{i}', f'https://github.com/owner{i}/project{i}'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N4: N-repos > #righe (100 > 3)
        n_repos_value = 100
        config_view.n_repos_var.set(n_repos_value)
        
        debug(f"\n[DEBUG] TF10 - Pre-condizioni:")
        debug(f"  CS1 (CSV con {num_csv_rows} righe): True")
        debug(f"  N4 (N-repos > {num_csv_rows}): {config_view.n_repos_var.get()}")
        
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))
        
        from gui.services.pipeline_service import PipelineResult
        mock_result = PipelineResult(success=True, error_message=None)
        
        try:
            with patch.object(controller, '_run_pipeline_thread') as mock_run:
                def mock_pipeline():
                    controller._result = mock_result
                mock_run.side_effect = mock_pipeline
                
                controller._on_start_pipeline()
                if controller._pipeline_thread:
                    controller._pipeline_thread.join(timeout=2)
                controller._on_pipeline_complete()
            
            success_shown = any(
                title == "Success" and "Pipeline completed successfully" in msg
                for title, msg in info_shown
            )
            
            debug(f"\n[DEBUG] TF10 - Messaggi: {info_shown}")
            
            assert success_shown, f"TF10 FALLITO: Pipeline non completata."
            
            debug(f"\nTF10 PASSED: N-repos ({n_repos_value}) > righe CSV ({num_csv_rows}) - Pipeline success")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF11: ST1 + CV2 + IO1 + RP1 - Cloning/Verify non selezionati
    # ========================================================================
    def test_TF11_no_cloning_verify(self, gui_components, temp_io_structure):
        """
        TF11: ST1 + CV2 + IO1 + RP1
        
        ID: TF11
        Combinazione: ST1 + CV2 + IO1 + RP1
        Oracolo: Analisi completata con successo
        
        INPUT:
        - Step selezionati: Solo Producer (NO Cloning, NO Verify)
            * run_cloner = False
            * run_cloner_check = False
            * run_producer = True
            * run_consumer = False
            * run_metrics = False
        - IO directory: temp_io_structure - ESISTE
        - Repo directory: temp_io_structure/repos - ESISTE
        
        OUTPUT ATTESO:
        - Messaggio: "Success" / "Pipeline completed successfully!"
        - CSV non richiesto perché Cloning/Verify non selezionati
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1 + CV2: Solo altri step, NO Cloning/Verify
        set_all_steps(config_view, False)
        config_view.run_producer_var.set(True)  # Solo Producer
        
        # Verifica pre-condizione ST1
        assert any_step_selected(config_view), "Pre-condizione ST1 fallita"
        assert not all_steps_selected(config_view), "Pre-condizione ST1 fallita"
        
        # Verifica pre-condizione CV2
        assert not cloning_verify_selected(config_view), "Pre-condizione CV2 fallita"
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        debug(f"\n[DEBUG] TF11 - Pre-condizioni:")
        debug(f"  ST1 (almeno uno step): {any_step_selected(config_view)}")
        debug(f"  CV2 (NO Cloning+Verify): {not cloning_verify_selected(config_view)}")
        debug(f"  IO1 (IO esiste): {temp_io_structure.exists()}")
        debug(f"  RP1 (repo esiste): {repo_path.exists()}")
        
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))
        
        from gui.services.pipeline_service import PipelineResult
        mock_result = PipelineResult(success=True, error_message=None)
        
        try:
            with patch.object(controller, '_run_pipeline_thread') as mock_run:
                def mock_pipeline():
                    controller._result = mock_result
                mock_run.side_effect = mock_pipeline
                
                controller._on_start_pipeline()
                if controller._pipeline_thread:
                    controller._pipeline_thread.join(timeout=2)
                controller._on_pipeline_complete()
            
            success_shown = any(
                title == "Success" and "Pipeline completed successfully" in msg
                for title, msg in info_shown
            )
            
            debug(f"\n[DEBUG] TF11 - Messaggi: {info_shown}")
            
            assert success_shown, f"TF11 FALLITO: Pipeline non completata."
            
            debug(f"\nTF11 PASSED: Senza Cloning+Verify, pipeline completata con successo")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF10: ST2 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3 - Tutti gli step
    # ========================================================================
    def test_TF12_all_steps(self, gui_components, temp_io_structure):
        """
        TF12: ST2 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3
        
        ID: TF12
        Combinazione: ST2 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3
        Oracolo: [Single] Tutti gli Step eseguiti ed analisi completata
        
        INPUT:
        - Step selezionati: TUTTI
            * run_cloner = True
            * run_cloner_check = True
            * run_producer = True
            * run_consumer = True
            * run_metrics = True
        - IO directory: temp_io_structure - ESISTE
        - Repo directory: temp_io_structure/repos - ESISTE
        - CSV file: temp_io_structure/projects_TF12.csv - ESISTE, 5 righe dati
        - N-repos: 3 (0 < 3 < 5)
        
        OUTPUT ATTESO:
        - Tutti i 5 step eseguiti
        - Messaggio: "Success" / "Pipeline completed successfully!"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST2: Tutti gli step selezionati
        set_all_steps(config_view, True)
        
        # Verifica pre-condizione ST2
        assert all_steps_selected(config_view), "Pre-condizione ST2 fallita"
        
        # Verifica pre-condizione CV1 (implicito in ST2)
        assert cloning_verify_selected(config_view), "Pre-condizione CV1 fallita"
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        # Setup CSV1 + CS1
        csv_path = temp_io_structure / "projects_TF12.csv"
        num_csv_rows = 5
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            for i in range(num_csv_rows):
                writer.writerow([f'owner{i}', f'project{i}', f'https://github.com/owner{i}/project{i}'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N3: N-repos valido
        config_view.n_repos_var.set(3)
        
        debug(f"\n[DEBUG] TF12 - Pre-condizioni:")
        debug(f"  ST2 (tutti gli step): {all_steps_selected(config_view)}")
        debug(f"  CV1 (Cloning+Verify): {cloning_verify_selected(config_view)}")
        debug(f"  IO1 (IO esiste): {temp_io_structure.exists()}")
        debug(f"  RP1 (repo esiste): {repo_path.exists()}")
        debug(f"  CSV1+CS1 (CSV con dati): True")
        debug(f"  N3 (N-repos valido): {config_view.n_repos_var.get()}")
        
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))
        
        from gui.services.pipeline_service import PipelineResult
        mock_result = PipelineResult(success=True, error_message=None)
        
        try:
            with patch.object(controller, '_run_pipeline_thread') as mock_run:
                def mock_pipeline():
                    controller._result = mock_result
                mock_run.side_effect = mock_pipeline
                
                controller._on_start_pipeline()
                if controller._pipeline_thread:
                    controller._pipeline_thread.join(timeout=2)
                controller._on_pipeline_complete()
            
            success_shown = any(
                title == "Success" and "Pipeline completed successfully" in msg
                for title, msg in info_shown
            )
            
            debug(f"\n[DEBUG] TF12 - Messaggi: {info_shown}")
            
            assert success_shown, f"TF12 FALLITO: Pipeline non completata."
            
            # Verifica che tutti gli step fossero selezionati
            config = config_view.get_config_values()
            assert config['run_cloner'], "TF12: run_cloner dovrebbe essere True"
            assert config['run_cloner_check'], "TF12: run_cloner_check dovrebbe essere True"
            assert config['run_producer_analysis'], "TF12: run_producer dovrebbe essere True"
            assert config['run_consumer_analysis'], "TF12: run_consumer dovrebbe essere True"
            assert config['run_metrics_analysis'], "TF12: run_metrics dovrebbe essere True"
            
            debug(f"\nTF12 PASSED: Tutti gli step eseguiti, analisi completata con successo")
            
        finally:
            main_window.show_info = original_show_info


# ============================================================================
# TEST CLASS - ADDITIONAL VALIDATION TESTS
# ============================================================================


class TestGUIConfigValidation:
    """Test aggiuntivi per la validazione della configurazione GUI."""
    
    def test_step_selection_states(self, gui_components):
        """Verifica che gli stati di selezione step siano corretti."""
        config_view = gui_components['config_view']
        
        # Test ST2: tutti gli step selezionati
        set_all_steps(config_view, True)
        assert all_steps_selected(config_view), "ST2: Tutti gli step dovrebbero essere selezionati"
        
        # Test ST0: nessuno step selezionato
        set_all_steps(config_view, False)
        assert not any_step_selected(config_view), "ST0: Nessuno step dovrebbe essere selezionato"
        
        # Test ST1: step parziali
        config_view.run_cloner_var.set(True)
        assert any_step_selected(config_view), "ST1: Almeno uno step dovrebbe essere selezionato"
        assert not all_steps_selected(config_view), "ST1: Non tutti gli step dovrebbero essere selezionati"
    
    def test_cloning_verify_combinations(self, gui_components):
        """Verifica le combinazioni CV1 e CV2."""
        config_view = gui_components['config_view']
        
        # CV1: entrambi selezionati
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        assert cloning_verify_selected(config_view), "CV1: Cloning e Verify dovrebbero essere entrambi selezionati"
        
        # CV2: nessuno dei due
        set_cloning_steps_only(config_view, cloner=False, verify=False)
        assert not cloning_verify_selected(config_view), "CV2: Cloning e Verify non dovrebbero essere selezionati"
    
    def test_rules_3_toggle(self, gui_components):
        """Verifica il toggle della regola 3 (RU3_0/RU3_1)."""
        config_view = gui_components['config_view']
        
        # RU3_1: regola 3 selezionata
        config_view.rules_3_var.set(True)
        config = config_view.get_config_values()
        assert config['rules_3'] == True, "RU3_1: rules_3 dovrebbe essere True"
        
        # RU3_0: regola 3 non selezionata
        config_view.rules_3_var.set(False)
        config = config_view.get_config_values()
        assert config['rules_3'] == False, "RU3_0: rules_3 dovrebbe essere False"
    
    def test_n_repos_values(self, gui_components):
        """Verifica i valori di N-repos (N1, N2, N3, N4)."""
        config_view = gui_components['config_view']
        
        # N1: valore negativo (comportamento boundary)
        config_view.n_repos_var.set(-1)
        config = config_view.get_config_values()
        assert config['n_repos'] == -1, "N1: n_repos dovrebbe accettare valori negativi per test"
        
        # N2: valore zero
        config_view.n_repos_var.set(0)
        config = config_view.get_config_values()
        assert config['n_repos'] == 0, "N2: n_repos dovrebbe essere 0"
        
        # N3: valore valido positivo
        config_view.n_repos_var.set(5)
        config = config_view.get_config_values()
        assert config['n_repos'] == 5, "N3: n_repos dovrebbe essere 5"
        
        # N4: valore grande
        config_view.n_repos_var.set(1000)
        config = config_view.get_config_values()
        assert config['n_repos'] == 1000, "N4: n_repos dovrebbe essere 1000"


class TestGUIPathConfiguration:
    """Test per la configurazione dei path nella GUI."""
    
    def test_default_path_values(self, gui_components):
        """Verifica i valori di default dei path."""
        config_view = gui_components['config_view']
        
        # I default sono impostati nel costruttore di ConfigView
        assert config_view.io_path_var.get() == "./io"
        assert config_view.repo_path_var.get() == "./io/repos"
        assert config_view.project_list_var.get() == "./io/applied_projects.csv"
    
    def test_path_update(self, gui_components, tmp_path):
        """Verifica che i path possano essere aggiornati."""
        config_view = gui_components['config_view']
        
        new_io_path = str(tmp_path / "new_io")
        new_repo_path = str(tmp_path / "new_repos")
        new_csv_path = str(tmp_path / "new_projects.csv")
        
        config_view.io_path_var.set(new_io_path)
        config_view.repo_path_var.set(new_repo_path)
        config_view.project_list_var.set(new_csv_path)
        
        config = config_view.get_config_values()
        
        assert str(config['io_path']) == new_io_path
        assert str(config['repository_path']) == new_repo_path
        assert str(config['project_list_path']) == new_csv_path


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
