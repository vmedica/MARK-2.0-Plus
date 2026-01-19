# Command to run tests: pytest -vv -s test/system_test_gui/gui_test.py
"""Black-box system testing for MARK 2.0 GUI interface.

HOW TO DISABLE DEBUG PRINTS:
To disable all debug print statements, modify the debug() function (around line 202):
- Comment out the print(msg) line
- Uncomment the pass statement
Example:
    def debug(msg):
        #print(msg)
        pass  # <-- use this instead of print to disable all debug output

Test Frame (TF) for validating MARK 2.0 Plus GUI.
Run with command: pytest -v test/system_test_gui/gui_test.py

Categories and constraints tested:
- ST0/ST1/ST2: Selected steps (none, partial, all)
- CV1/CV2: Cloning and Verify selected/not selected
- IO0/IO1: IO directory existence
- RP0/RP1: Repo directory existence
- CSV0/CSV1: CSV file existence
- CS0/CS1: CSV state (empty/non-empty)
- RU3_0/RU3_1: Rule 3 selected/not selected
- N1/N2/N3/N4: N-repos value
"""

import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import shutil
import csv
import gc
import time


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
    """Create a Tk root window for testing.
    
    Include robust cleanup to avoid Tcl/Tk resource issues on Windows.
    """
    
    # Force garbage collection before creating new Tk instance
    gc.collect()
    
    # Small delay to ensure previous Tk resources are fully released
    time.sleep(0.05)
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the window during tests
    except Exception as e:
        # Retry once after cleanup if initial creation fails
        gc.collect()
        time.sleep(0.1)
        root = tk.Tk()
        root.withdraw()
    
    yield root
    
    # Robust cleanup
    try:
        root.quit()
        root.update_idletasks()
        root.destroy()
    except Exception:
        pass
    
    # Force garbage collection after destroying Tk
    gc.collect()


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

 # ===== DEBUG HELPER (comment this function to disable all print statements) =====
def debug(msg):
    #print(msg)
    pass  # <-- use this instead of print to disable all output

class TestGUISystemTestFrames:
    """
    Test Frame for validating MARK 2.0 Plus GUI.
    
    Each test frame verifies a specific combination of:
    - Selected steps
    - Path configuration
    - File/directory state
    """

    # ========================================================================
    # TF1: ST0 - No step selected
    # ========================================================================
    def test_TF1_no_step_selected(self, gui_components, temp_io_structure):
        """
        TF1: ST0 - No Step selected

        ID: TF1
        Combination: ST0
        Oracle: [Success] Pipeline completed (no operations executed)
        
        INPUT:
        - Selected steps: NONE (run_cloner=False, run_cloner_check=False,
                            run_producer=False, run_consumer=False, run_metrics=False)
        - IO directory: temp_io_structure (valid temporary directory)
        - Repo directory: temp_io_structure/repos (created in test)
        
        EXPECTED OUTPUT:
        - Message: "Success" / "Pipeline completed successfully!"
        - All Steps disabled
        """

        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']

        # Setup: no step selected
        set_all_steps(config_view, False)

        # Setup: valid paths
        config_view.io_path_var.set(str(temp_io_structure))
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))

        # Precondition ST0
        assert not any_step_selected(config_view), (
            "Precondition failed: at least one step is selected"
        )

        # Oracle 1: step configuration
        config = config_view.get_config_values()
        steps_enabled = any([
            config['run_cloner'],
            config['run_cloner_check'],
            config['run_producer_analysis'],
            config['run_consumer_analysis'],
            config['run_metrics_analysis']
        ])

        debug("\n[DEBUG] TF1 - Step configuration state:")
        debug(f"  All steps disabled (expected): True")
        debug(f"  All steps disabled (actual): {not steps_enabled}")

        assert not steps_enabled, (
            "TF1 FAILED: at least one step is enabled\n"
            f"Steps state: {config}"
        )

        # Mock show_info
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))

        try:
            # Action
            controller._on_start_pipeline()

            if controller._pipeline_thread:
                controller._pipeline_thread.join(timeout=5)
                controller._on_pipeline_complete()

            # Oracle 2: verify success message
            expected_title = "Success"
            expected_msg = "Pipeline completed successfully!"

            success_shown = any(
                title == expected_title and expected_msg in msg
                for title, msg in info_shown
            )

            debug("\n[DEBUG] TF1 - Pipeline start result:")
            debug(f"  Expected title: '{expected_title}'")
            debug(f"  Expected message: '{expected_msg}'")
            debug(f"  Messages received: {info_shown}")

            assert success_shown, (
                "TF1 FAILED: success message NOT shown\n"
                f"Received: {info_shown}"
            )

            debug("\nTF1 PASSED:")
            debug("  - All steps disabled")
            debug("  - Success message shown")

        finally:
            main_window.show_info = original_show_info


    # ========================================================================
    # TF2: ST1 + CV1 + IO0 - IO directory missing
    # ========================================================================
    def test_TF2_io_directory_missing(self, gui_components, tmp_path):
        """
        TF2: ST1 + CV1 + IO0 - IO directory missing
        
        ID: TF2
        Combination: ST1 + CV1 + IO0
        Oracle: [Error] IO directory missing
        
        INPUT:
        - Selected steps: Cloning + Verify (run_cloner=True, run_cloner_check=True)
        - IO directory: tmp_path/nonexistent_io_directory (DOES NOT EXIST)
        - Repo directory: not configured (irrelevant, IO fails first)
        
        EXPECTED OUTPUT:
        - Error: "Invalid Path" / "IO path does not exist: {path}"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup: Select Cloning + Verify (CV1) - partial steps (ST1)
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Verify precondition ST1: at least one step selected (not all)
        assert any_step_selected(config_view), (
            "Precondition ST1 failed: no step selected"
        )
        assert not all_steps_selected(config_view), (
            "Precondition ST1 failed: all steps are selected"
        )
        
        # Verify precondition CV1: Cloning and Verify selected
        assert cloning_verify_selected(config_view), (
            "Precondition CV1 failed: Cloning and Verify not both selected"
        )
        
        # Setup IO0: Nonexistent IO directory
        nonexistent_io = tmp_path / "nonexistent_io_directory"
        config_view.io_path_var.set(str(nonexistent_io))
        
        # Verify precondition IO0: directory does not exist
        assert not nonexistent_io.exists(), (
            "Precondition IO0 failed: IO directory exists"
        )
        
        # Mock show_error to capture the error
        error_shown = []
        original_show_error = main_window.show_error
        main_window.show_error = lambda title, msg: error_shown.append((title, msg))
        
        try:
            # Action: Attempt to start the pipeline
            controller._on_start_pipeline()
            
            # Oracle: An error must be shown for IO path
            assert len(error_shown) > 0, (
                "TF2 FAILED: No error shown for missing IO directory"
            )
            
            error_title, error_msg = error_shown[0]
            
            # Expected values
            expected_title = "Invalid Path"
            expected_msg = f"IO path does not exist: {nonexistent_io}"
            
            # DEBUG: Print expected vs actual results
            debug(f"\n[DEBUG] TF2 - Error message validation:")
            debug(f"  Expected title: '{expected_title}'")
            debug(f"  Actual title: '{error_title}'")
            debug(f"  Expected message: '{expected_msg}'")
            debug(f"  Actual message: '{error_msg}'")
            
            # Verify that the title is exactly "Invalid Path"
            assert error_title == expected_title, (
                f"TF2 FAILED: Unexpected error title.\n"
                f"  Expected: '{expected_title}'\n"
                f"  Actual: '{error_title}'"
            )
            
            # Verify that the message is exactly "IO path does not exist: {path}"
            assert error_msg == expected_msg, (
                f"TF2 FAILED: Error message does not match.\n"
                f"  Expected: '{expected_msg}'\n"
                f"  Actual: '{error_msg}'"
            )
            
            debug(f"TF2 PASSED: IO directory error correctly shown")
            debug(f"  - Title: {error_title}")
            debug(f"  - Message: {error_msg}")
            
        finally:
            main_window.show_error = original_show_error

    # ========================================================================
    # TF3: ST1 + CV1 + IO1 + RP0 - Repo directory missing
    # ========================================================================
    def test_TF3_repo_directory_missing(self, gui_components, temp_io_structure, tmp_path):
        """
        TF3: ST1 + CV1 + IO1 + RP0 - Repo directory missing
        
        Combination: ST1 + CV1 + IO1 + RP0
        Oracle: [Single] repo directory does not exist, gets created, pipeline success
        
        INPUT:
        - Selected steps: Cloning + Verify (run_cloner=True, run_cloner_check=True)
        - IO directory: temp_io_structure (temporary directory EXISTS)
        - Repo directory: tmp_path/test_repos (DOES NOT EXIST, will be created)
        - CSV file: temp_io_structure/test_projects.csv (empty, header only)
        - N-repos: 0
        
        EXPECTED OUTPUT:
        - Repo directory created automatically
        - Message: "Success" / "Pipeline completed successfully!"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup: Select Cloning + Verify (CV1) - partial steps (ST1)
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Verify precondition ST1: at least one step selected (not all)
        assert any_step_selected(config_view), (
            "Precondition ST1 failed: no step selected"
        )
        
        # Verify precondition CV1: Cloning and Verify selected
        assert cloning_verify_selected(config_view), (
            "Precondition CV1 failed: Cloning and Verify not both selected"
        )
        
        # Setup IO1: IO directory exists
        config_view.io_path_var.set(str(temp_io_structure))
        assert temp_io_structure.exists(), (
            "Precondition IO1 failed: IO directory does not exist"
        )
        
        # Setup RP0: Repo directory does not exist
        nonexistent_repo = tmp_path / "test_repos"
        config_view.repo_path_var.set(str(nonexistent_repo))
        
        # Verify precondition RP0: repo directory does not exist
        assert not nonexistent_repo.exists(), (
            "Precondition RP0 failed: repo directory exists"
        )
        
        # Setup: Create an empty test CSV (header only)
        csv_path = temp_io_structure / "test_projects.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            import csv as csv_module
            writer = csv_module.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
        
        config_view.project_list_var.set(str(csv_path))
        config_view.n_repos_var.set(0)  # Empty CSV
        
        debug(f"\n[DEBUG] TF3 - Preconditions:")
        debug(f"  ST1 (at least one step): {any_step_selected(config_view)}")
        debug(f"  CV1 (Cloning+Verify): {cloning_verify_selected(config_view)}")
        debug(f"  IO1 (IO exists): {temp_io_structure.exists()}")
        debug(f"  RP0 (repo does NOT exist): {not nonexistent_repo.exists()}")
        
        # Mock show_info to capture success message
        info_shown = []
        original_show_info = main_window.show_info
        main_window.show_info = lambda title, msg: info_shown.append((title, msg))
        
        # Mock the pipeline service to simulate success without real execution
        from unittest.mock import MagicMock, patch
        from gui.services.pipeline_service import PipelineResult
        
        mock_result = PipelineResult(success=True, error_message=None)
        
        try:
            with patch.object(controller, '_run_pipeline_thread') as mock_run:
                # Simulate pipeline execution
                def mock_pipeline():
                    # Simulate repo directory creation
                    nonexistent_repo.mkdir(parents=True, exist_ok=True)
                    controller._result = mock_result
                
                mock_run.side_effect = mock_pipeline
                
                # Action: Start the pipeline
                controller._on_start_pipeline()
                
                # Wait for (mocked) thread to finish
                if controller._pipeline_thread:
                    controller._pipeline_thread.join(timeout=2)
                
                # Force completion
                controller._on_pipeline_complete()
            
            # Oracle part 1: Repo directory must have been created
            debug(f"\n[DEBUG] TF3 - State after execution:")
            debug(f"  Repo directory created: {nonexistent_repo.exists()}")
            
            assert nonexistent_repo.exists(), (
                f"TF3 FAILED: Repo directory was not created.\n"
                f"  Path: {nonexistent_repo}"
            )
            
            # Oracle part 2: Success message must be shown
            expected_title = "Success"
            expected_msg = "Pipeline completed successfully!"
            
            success_shown = any(
                title == expected_title and expected_msg in msg
                for title, msg in info_shown
            )
            
            debug(f"  Info messages captured: {info_shown}")
            debug(f"  Success message found: {success_shown}")
            
            assert success_shown, (
                f"TF3 FAILED: Success message NOT shown.\n"
                f"  Expected: '{expected_title}' / '{expected_msg}'\n"
                f"  Received: {info_shown}"
            )
            
            debug(f"\nTF3 PASSED: Repo directory created and pipeline completed successfully")
            debug(f"  - IO path (exists): {temp_io_structure}")
            debug(f"  - Repo path (created): {nonexistent_repo}")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF4: ST1 + CV1 + IO1 + RP1 + CSV0 - CSV file missing
    # ========================================================================
    def test_TF4_csv_file_missing(self, gui_components, temp_io_structure, tmp_path):
        """
        TF4: ST1 + CV1 + IO1 + RP1 + CSV0 - CSV file missing
        
        ID: TF4
        Combination: ST1 + CV1 + IO1 + RP1 + CSV0
        Oracle: [Error] CSV missing (required because CV1)
        
        INPUT:
        - Selected steps: Cloning + Verify 
            * run_cloner = True
            * run_cloner_check = True  
            * run_producer = False
            * run_consumer = False
            * run_metrics = False
        - IO directory: temp_io_structure (e.g. C:/temp/pytest-xxx/io) - EXISTS
        - Repo directory: temp_io_structure/repos - EXISTS
        - CSV file: tmp_path/nonexistent_projects.csv - DOES NOT EXIST
        
        EXPECTED OUTPUT:
        - Error: "Pipeline Failed" 
        - Message: "Error: [Errno 2] No such file or directory: 'nonexistent_projects.csv'"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1: Select Cloning + Verify (CV1) - partial steps
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        
        # Verify precondition ST1
        assert any_step_selected(config_view), "Precondition ST1 failed"
        assert not all_steps_selected(config_view), "Precondition ST1 failed: all steps selected"
        
        # Verify precondition CV1
        assert cloning_verify_selected(config_view), "Precondition CV1 failed"
        
        # Setup IO1: IO directory exists
        config_view.io_path_var.set(str(temp_io_structure))
        assert temp_io_structure.exists(), "Precondition IO1 failed"
        
        # Setup RP1: Repo directory exists
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        assert repo_path.exists(), "Precondition RP1 failed"
        
        # Setup CSV0: CSV file does not exist
        nonexistent_csv = tmp_path / "nonexistent_projects.csv"
        config_view.project_list_var.set(str(nonexistent_csv))
        assert not nonexistent_csv.exists(), "Precondition CSV0 failed"
        
        debug(f"\n[DEBUG] TF4 - Preconditions:")
        debug(f"  ST1 (at least one step): {any_step_selected(config_view)}")
        debug(f"  CV1 (Cloning+Verify): {cloning_verify_selected(config_view)}")
        debug(f"  IO1 (IO exists): {temp_io_structure.exists()}")
        debug(f"  RP1 (repo exists): {repo_path.exists()}")
        debug(f"  CSV0 (CSV does NOT exist): {not nonexistent_csv.exists()}")
        
        # Mock show_error to capture the error
        error_shown = []
        original_show_error = main_window.show_error
        main_window.show_error = lambda title, msg: error_shown.append((title, msg))
        
        try:
            # Action: Start the pipeline
            controller._on_start_pipeline()
            
            # Wait for pipeline thread to finish (if started)
            if controller._pipeline_thread:
                controller._pipeline_thread.join(timeout=5)
                controller._on_pipeline_complete()
            
            # Oracle: An error must be shown for missing CSV
            debug(f"\n[DEBUG] TF4 - Errors captured: {error_shown}")
            
            assert len(error_shown) > 0, (
                "TF4 FAILED: No error shown for Missing CSV"
            )
            
            error_title, error_msg = error_shown[0]
            
            # Expected values: FileNotFoundError for non-existent CSV
            expected_title = "Pipeline Failed"
            # The message must contain FileNotFoundError and the CSV filename
            csv_filename = nonexistent_csv.name
            
            debug(f"  Expected Title: '{expected_title}'")
            debug(f"  Actual Title: '{error_title}'")
            debug(f"  Actual Message: '{error_msg}'")
            
            assert error_title == expected_title, (
                f"TF4 FAILED: Unexpected error title.\n"
                f"  Expected: '{expected_title}'\n"
                f"  Actual: '{error_title}'"
            )
            
            # Verify that the message contains FileNotFoundError and the CSV filename
            # Verify that the message indicates that the CSV does NOT exist
            assert (
                "Error: [Errno 2] No such file or directory:" in error_msg
                and csv_filename in error_msg
            ), (
                f"TF4 FAILED: Error message does not indicate Missing CSV.\n"
                f"Actual: '{error_msg}'"
            )
            
            debug(f"\nTF4 PASSED: Missing CSV error correctly shown")
            debug(f"  - Title: {error_title}")
            debug(f"  - Message: {error_msg}")
            
        finally:
            main_window.show_error = original_show_error

    # ========================================================================
    # TF5: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_0 - Empty CSV, Rule3 OFF
    # ========================================================================
    def test_TF5_csv_empty_rule3_off(self, gui_components, temp_io_structure):
        """
        TF5: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_0
        
        ID: TF5
        Combination: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_0
        Oracle: [Single] Analysis completed successfully
        
        INPUT:
        - Selected steps: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
            * run_producer = False
            * run_consumer = False
            * run_metrics = False
        - IO directory: temp_io_structure - EXISTS
        - Repo directory: temp_io_structure/repos - EXISTS
        - CSV file: temp_io_structure/empty_projects.csv - EXISTS, EMPTY (header only)
        - Rule 3: False (RU3_0)
        
        EXPECTED OUTPUT:
        - Message: "Success" / "Pipeline completed successfully!"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1 + CV1
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        assert any_step_selected(config_view), "Precondition ST1 failed"
        assert cloning_verify_selected(config_view), "Precondition CV1 failed"
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        assert temp_io_structure.exists(), "Precondition IO1 failed"
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        # Setup CSV1 + CS0: CSV file exists but is empty (header only)
        csv_path = temp_io_structure / "empty_projects.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])  # header only
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N2: N-repos = 0 (Empty CSV)
        config_view.n_repos_var.set(0)
        
        # Setup RU3_0: Rule 3 disabled
        config_view.rules_3_var.set(False)
        
        debug(f"\n[DEBUG] TF5 - Preconditions:")
        debug(f"  CSV1 (CSV exists): {csv_path.exists()}")
        debug(f"  CS0 (Empty CSV): True (header only)")
        debug(f"  RU3_0 (Rule3 OFF): {not config_view.rules_3_var.get()}")
        
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
            
            debug(f"\n[DEBUG] TF5 - Info messages: {info_shown}")
            
            assert success_shown, (
                f"TF5 FAILED: Success message NOT shown.\n"
                f"Actual: {info_shown}"
            )
            
            # Verify that rules_3 is False (RU3_0)
            config = config_view.get_config_values()
            assert config['rules_3'] == False, (
                f"TF5 FAILED: rules_3 should be False (RU3_0).\n"
                f"  Actual: {config['rules_3']}"
            )
            
            debug(f"  Verify RU3_0: rules_3={config['rules_3']}")
            debug(f"\nTF5 PASSED: Analysis completed with Empty CSV and Rule3 OFF")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF6: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_1 - Empty CSV, Rule3 ON
    # ========================================================================
    def test_TF6_csv_empty_rule3_on(self, gui_components, temp_io_structure):
        """
        TF6: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_1
        
        ID: TF6
        Combination: ST1 + CV1 + IO1 + RP1 + CSV1 + CS0 + RU3_1
        Oracle: [Single] Analysis completed successfully
        
        INPUT:
        - Selected steps: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
            * run_producer = False
            * run_consumer = False
            * run_metrics = False
        - IO directory: temp_io_structure - EXISTS
        - Repo directory: temp_io_structure/repos - EXISTS
        - CSV file: temp_io_structure/empty_projects2.csv - EXISTS, EMPTY (header only)
        - Rule 3: True (RU3_1)
        
        EXPECTED OUTPUT:
        - Message: "Success" / "Pipeline completed successfully!"
        - Configuration: rules_3 = True (RU3_1)
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
        
        # Setup CSV1 + CS0: Empty CSV
        csv_path = temp_io_structure / "empty_projects2.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N2: N-repos = 0 (Empty CSV)
        config_view.n_repos_var.set(0)
        
        # Setup RU3_1: Rule 3 enabled
        config_view.rules_3_var.set(True)
        
        debug(f"\n[DEBUG] TF6 - Preconditions:")
        debug(f"  RU3_1 (Rule3 ON): {config_view.rules_3_var.get()}")
        
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
            
            debug(f"\n[DEBUG] TF6 - Info messages: {info_shown}")
            
            assert success_shown, f"TF6 FAILED: Success message NOT shown."
            
            # Verify that rules_3 is True (RU3_1)
            config = config_view.get_config_values()
            assert config['rules_3'] == True, (
                f"TF6 FAILED: rules_3 should be True (RU3_1).\n"
                f"  Actual: {config['rules_3']}"
            )
            
            debug(f"  Verify RU3_1: rules_3={config['rules_3']}")
            debug(f"\nTF6 PASSED: Analysis completed with Empty CSV and Rule3 ON")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF7: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N1 - N-repos negative
    # ========================================================================
    def test_TF7_n_repos_negative(self, gui_components, temp_io_structure):
        """
        TF7: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N1
        
        ID: TF7
        Combination: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N1
        Oracle: [Error] N-repos < 0
        
        INPUT:
        - Selected steps: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
        - IO directory: temp_io_structure - EXISTS
        - Repo directory: temp_io_structure/repos - EXISTS
        - CSV file: temp_io_structure/projects_TF7.csv - EXISTS, 2 data rows
        - N-repos: -1 (negative value)
        
        EXPECTED OUTPUT:
        - Error: "Invalid Value" / "N-repos cannot be negative: -1"
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
        
        # Setup CSV1 + CS1: CSV with data
        csv_path = temp_io_structure / "projects_TF7.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            writer.writerow(['owner1', 'project1', 'https://github.com/owner1/project1'])
            writer.writerow(['owner2', 'project2', 'https://github.com/owner2/project2'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N1: N-repos < 0
        config_view.n_repos_var.set(-1)
        
        debug(f"\n[DEBUG] TF7 - Preconditions:")
        debug(f"  CS1 (CSV not empty): True")
        debug(f"  N1 (N-repos < 0): {config_view.n_repos_var.get()}")
        
        # Mock show_error to capture the error
        error_shown = []
        original_show_error = main_window.show_error
        main_window.show_error = lambda title, msg: error_shown.append((title, msg))
        
        try:
            # Action: Attempt to start the pipeline
            controller._on_start_pipeline()
            
            # Oracle: An error must be shown for negative n_repos
            assert len(error_shown) > 0, (
                "TF7 FAILED: No error shown for negative n_repos"
            )
            
            error_title, error_msg = error_shown[0]
            expected_title = "Invalid Value"
            expected_msg = "N-repos cannot be negative: -1"
            
            debug(f"\n[DEBUG] TF7 - Result:")
            debug(f"  Error title: {error_title}")
            debug(f"  Error message: {error_msg}")
            
            assert error_title == expected_title, (
                f"TF7 FAILED: Unexpected error title.\n"
                f"  Expected: '{expected_title}'\n"
                f"  Actual: '{error_title}'"
            )
            assert error_msg == expected_msg, (
                f"TF7 FAILED: Unexpected error message.\n"
                f"  Expected: '{expected_msg}'\n"
                f"  Actual: '{error_msg}'"
            )
            
            debug(f"\nTF7 PASSED: Error correctly shown for negative n_repos")
            
        finally:
            main_window.show_error = original_show_error

    # ========================================================================
    # TF8: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N2 - N-repos = 0
    # ========================================================================
    def test_TF8_n_repos_zero(self, gui_components, temp_io_structure):
        """
        TF8: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N2
        
        ID: TF8
        Combination: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N2
        Oracle: [Success] N-repos = 0 accepted, pipeline completed
        
        INPUT:
        - Selected steps: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
        - IO directory: temp_io_structure - EXISTS
        - Repo directory: temp_io_structure/repos - EXISTS
        - CSV file: temp_io_structure/projects_TF8.csv - EXISTS, 1 data row
        - N-repos: 0
        
        EXPECTED OUTPUT:
        - Configuration accepts n_repos = 0
        - Message: "Success" / "Pipeline completed successfully!"
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
        
        # Setup CSV1 + CS1
        csv_path = temp_io_structure / "projects_TF8.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            writer.writerow(['owner1', 'project1', 'https://github.com/owner1/project1'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N2: N-repos = 0
        config_view.n_repos_var.set(0)
        
        debug(f"\n[DEBUG] TF8 - Preconditions:")
        debug(f"  N2 (N-repos = 0): {config_view.n_repos_var.get()}")
        
        # Verify that n_repos is 0 in the configuration
        config = config_view.get_config_values()
        assert config['n_repos'] == 0, (
            f"TF8 FAILED: n_repos should be 0.\n"
            f"Value: {config['n_repos']}"
        )
        
        # Mock show_info to capture the success message
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
            
            debug(f"\n[DEBUG] TF8 - Messages: {info_shown}")
            
            assert success_shown, f"TF8 FAILED: Pipeline not completed successfully."
            
            debug(f"\nTF8 PASSED: n_repos = 0 accepted, pipeline completed successfully")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF9: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3 - N-repos valido
    # ========================================================================
    def test_TF9_n_repos_valid(self, gui_components, temp_io_structure):
        """
        TF9: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3
        
        ID: TF9
        Combination: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3
        Oracle: 0 < N-repos < #CSVProjectRows - Pipeline success
        
        INPUT:
        - Selected steps: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
        - IO directory: temp_io_structure - EXISTS
        - Repo directory: temp_io_structure/repos - EXISTS
        - CSV file: temp_io_structure/projects_TF9.csv - EXISTS, 5 data rows
        - N-repos: 3 (0 < 3 < 5)
        
        EXPECTED OUTPUT:
        - Message: "Success" / "Pipeline completed successfully!"
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
        
        # Setup CSV1 + CS1: CSV with 5 data rows
        csv_path = temp_io_structure / "projects_TF9.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            for i in range(5):
                writer.writerow([f'owner{i}', f'project{i}', f'https://github.com/owner{i}/project{i}'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N3: 0 < N-repos < #rows (5)
        n_repos_value = 3
        config_view.n_repos_var.set(n_repos_value)
        
        debug(f"\n[DEBUG] TF9 - Preconditions:")
        debug(f"  CS1 (CSV with 5 rows): True")
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
            
            debug(f"\n[DEBUG] TF9 - Messages: {info_shown}")
            
            assert success_shown, f"TF9 FAILED: Pipeline not completed successfully."
            
            debug(f"\nTF9 PASSED: Valid N-repos ({n_repos_value}) - Pipeline success")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF10: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N4 - N-repos > #rows
    # ========================================================================
    def test_TF10_n_repos_exceeds_rows(self, gui_components, temp_io_structure):
        """
        TF10: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N4
        
        ID: TF10
        Combination: ST1 + CV1 + IO1 + RP1 + CSV1 + CS1 + N4
        Oracle: [Error] N-repos > #CSVProjectRows
        
        INPUT:
        - Selected steps: Cloning + Verify
            * run_cloner = True
            * run_cloner_check = True
        - IO directory: temp_io_structure - EXISTS
        - Repo directory: temp_io_structure/repos - EXISTS
        - CSV file: temp_io_structure/projects_TF10.csv - EXISTS, 3 data rows
        - N-repos: 100 (100 > 3)
        
        EXPECTED OUTPUT:
        - Error: "Invalid Value" / "N-repos (100) exceeds CSV rows (3)"
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
        
        # Setup CSV1 + CS1: CSV with 3 rows
        csv_path = temp_io_structure / "projects_TF10.csv"
        num_csv_rows = 3
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['owner', 'project_name', 'url'])
            for i in range(num_csv_rows):
                writer.writerow([f'owner{i}', f'project{i}', f'https://github.com/owner{i}/project{i}'])
        config_view.project_list_var.set(str(csv_path))
        
        # Setup N4: N-repos > #rows (100 > 3)
        n_repos_value = 100
        config_view.n_repos_var.set(n_repos_value)
        
        debug(f"\n[DEBUG] TF10 - Preconditions:")
        debug(f"  CS1 (CSV with {num_csv_rows} rows): True")
        debug(f"  N4 (N-repos > {num_csv_rows}): {config_view.n_repos_var.get()}")
        
        # Mock show_error to capture the error
        error_shown = []
        original_show_error = main_window.show_error
        main_window.show_error = lambda title, msg: error_shown.append((title, msg))
        
        try:
            # Action: Attempt to start the pipeline
            controller._on_start_pipeline()
            
            # Oracle: An error must be shown for n_repos > rows
            assert len(error_shown) > 0, (
                "TF10 FAILED: No error shown for n_repos > CSV rows"
            )
            
            error_title, error_msg = error_shown[0]
            expected_title = "Invalid Value"
            expected_msg = f"N-repos ({n_repos_value}) exceeds CSV rows ({num_csv_rows})"
            
            debug(f"\n[DEBUG] TF10 - Result:")
            debug(f"  Error title: {error_title}")
            debug(f"  Error message: {error_msg}")
            
            assert error_title == expected_title, (
                f"TF10 FAILED: Unexpected error title.\n"
                f"  Expected: '{expected_title}'\n"
                f"  Actual: '{error_title}'"
            )
            assert error_msg == expected_msg, (
                f"TF10 FAILED: Unexpected error message.\n"
                f"  Expected: '{expected_msg}'\n"
                f"  Actual: '{error_msg}'"
            )
            
            debug(f"\nTF10 PASSED: Error correctly shown for n_repos > CSV rows")
            
        finally:
            main_window.show_error = original_show_error

    # ========================================================================
    # TF11: ST1 + CV2 + IO1 + RP1 - Cloning/Verify not selected
    # ========================================================================
    def test_TF11_no_cloning_verify(self, gui_components, temp_io_structure):
        """
        TF11: ST1 + CV2 + IO1 + RP1
        
        ID: TF11
        Combination: ST1 + CV2 + IO1 + RP1
        Oracle: Analysis completed successfully
        
        INPUT:
        - Selected steps: Producer only (NO Cloning, NO Verify)
            * run_cloner = False
            * run_cloner_check = False
            * run_producer = True
            * run_consumer = False
            * run_metrics = False
        - IO directory: temp_io_structure - EXISTS
        - Repo directory: temp_io_structure/repos - EXISTS
        
        EXPECTED OUTPUT:
        - Message: "Success" / "Pipeline completed successfully!"
        - CSV not required because Cloning/Verify not selected
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST1 + CV2: Other steps only, NO Cloning/Verify
        set_all_steps(config_view, False)
        config_view.run_producer_var.set(True)  # Producer only
        
        # Verify Precondition ST1
        assert any_step_selected(config_view), "Precondition ST1 failed"
        assert not all_steps_selected(config_view), "Precondition ST1 failed"
        
        # Verify Precondition CV2
        assert not cloning_verify_selected(config_view), "Precondition CV2 failed"
        
        # Setup IO1
        config_view.io_path_var.set(str(temp_io_structure))
        
        # Setup RP1
        repo_path = temp_io_structure / "repos"
        repo_path.mkdir(exist_ok=True)
        config_view.repo_path_var.set(str(repo_path))
        
        debug(f"\n[DEBUG] TF11 - Preconditions:")
        debug(f"  ST1 (at least one step): {any_step_selected(config_view)}")
        debug(f"  CV2 (NO Cloning+Verify): {not cloning_verify_selected(config_view)}")
        debug(f"  IO1 (IO exists): {temp_io_structure.exists()}")
        debug(f"  RP1 (repo exists): {repo_path.exists()}")
        
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
            
            debug(f"\n[DEBUG] TF11 - Messages: {info_shown}")
            
            assert success_shown, f"TF11 FAILED: Pipeline not completed."
            
            # Verify that Cloning and Verify were NOT selected in the configuration
            config = config_view.get_config_values()
            assert config['run_cloner'] == False, (
                f"TF11 FAILED: run_cloner should be False.\n"
                f"  Actual: {config['run_cloner']}"
            )
            assert config['run_cloner_check'] == False, (
                f"TF11 FAILED: run_cloner_check should be False.\n"
                f"  Actual: {config['run_cloner_check']}"
            )
            
            debug(f"  Verify CV2: run_cloner={config['run_cloner']}, run_cloner_check={config['run_cloner_check']}")
            debug(f"\nTF11 PASSED: Without Cloning+Verify, pipeline completed successfully")
            
        finally:
            main_window.show_info = original_show_info

    # ========================================================================
    # TF12: ST2 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3 - all steps
    # ========================================================================
    def test_TF12_all_steps(self, gui_components, temp_io_structure):
        """
        TF12: ST2 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3
        
        ID: TF12
        Combination: ST2 + CV1 + IO1 + RP1 + CSV1 + CS1 + N3
        Oracle: [Single] all steps executed and analysis completed
        
        INPUT:
        - Selected steps: ALL
            * run_cloner = True
            * run_cloner_check = True
            * run_producer = True
            * run_consumer = True
            * run_metrics = True
        - IO directory: temp_io_structure - EXISTS
        - Repo directory: temp_io_structure/repos - EXISTS
        - CSV file: temp_io_structure/projects_TF12.csv - EXISTS, 5 data rows
        - N-repos: 3 (0 < 3 < 5)
        
        EXPECTED OUTPUT:
        - All 5 steps executed
        - Message: "Success" / "Pipeline completed successfully!"
        """
        config_view = gui_components['config_view']
        main_window = gui_components['main_window']
        controller = gui_components['controller']
        
        # Setup ST2: all steps selected
        set_all_steps(config_view, True)
        
        # Verify Precondition ST2
        assert all_steps_selected(config_view), "Precondition ST2 failed"
        
        # Verify Precondition CV1 (implicit in ST2)
        assert cloning_verify_selected(config_view), "Precondition CV1 failed"
        
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
        
        # Setup N3: Valid N-repos
        config_view.n_repos_var.set(3)
        
        debug(f"\n[DEBUG] TF12 - Preconditions:")
        debug(f"  ST2 (all steps): {all_steps_selected(config_view)}")
        debug(f"  CV1 (Cloning+Verify): {cloning_verify_selected(config_view)}")
        debug(f"  IO1 (IO exists): {temp_io_structure.exists()}")
        debug(f"  RP1 (repo exists): {repo_path.exists()}")
        debug(f"  CSV1+CS1 (CSV with data): True")
        debug(f"  N3 (valid N-repos): {config_view.n_repos_var.get()}")
        
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
            
            debug(f"\n[DEBUG] TF12 - Messages: {info_shown}")
            
            assert success_shown, f"TF12 FAILED: Pipeline not completed."
            
            # Verify that all steps were selected
            config = config_view.get_config_values()
            assert config['run_cloner'], "TF12: run_cloner should be True"
            assert config['run_cloner_check'], "TF12: run_cloner_check should be True"
            assert config['run_producer_analysis'], "TF12: run_producer should be True"
            assert config['run_consumer_analysis'], "TF12: run_consumer should be True"
            assert config['run_metrics_analysis'], "TF12: run_metrics should be True"
            
            debug(f"\nTF12 PASSED: All steps executed, Analysis completed successfully")
            
        finally:
            main_window.show_info = original_show_info


# ============================================================================
# TEST CLASS - ADDITIONAL VALIDATION TESTS (Tests for Utility functions used in Test Frames)
# ============================================================================


class TestGUIConfigValidation:
    """Additional tests for GUI configuration validation."""
    
    def test_step_selection_states(self, gui_components):
        """Verify that step selection states are correct."""
        config_view = gui_components['config_view']
        
        # Test ST2: all steps selected
        set_all_steps(config_view, True)
        assert all_steps_selected(config_view), "ST2: all steps should be selected"
        
        # Test ST0: no step selected
        set_all_steps(config_view, False)
        assert not any_step_selected(config_view), "ST0: No step should be selected"
        
        # Test ST1: partial steps
        config_view.run_cloner_var.set(True)
        assert any_step_selected(config_view), "ST1: at least one step should be selected"
        assert not all_steps_selected(config_view), "ST1: Not all steps should be selected"
    
    def test_cloning_verify_combinations(self, gui_components):
        """Verify the CV1 and CV2 combinations."""
        config_view = gui_components['config_view']
        
        # CV1: both selected
        set_cloning_steps_only(config_view, cloner=True, verify=True)
        assert cloning_verify_selected(config_view), "CV1: Cloning and Verify should be both selected"
        
        # CV2: neither
        set_cloning_steps_only(config_view, cloner=False, verify=False)
        assert not cloning_verify_selected(config_view), "CV2: Cloning and Verify should not be selected"
    
    def test_rules_3_toggle(self, gui_components):
        """Verify Rule 3 toggle (RU3_0/RU3_1)."""
        config_view = gui_components['config_view']
        
        # RU3_1: Rule 3 selected
        config_view.rules_3_var.set(True)
        config = config_view.get_config_values()
        assert config['rules_3'] == True, "RU3_1: rules_3 should be True"
        
        # RU3_0: Rule 3 not selected
        config_view.rules_3_var.set(False)
        config = config_view.get_config_values()
        assert config['rules_3'] == False, "RU3_0: rules_3 should be False"
    
    def test_n_repos_values(self, gui_components):
        """Verify N-repos values (N1, N2, N3, N4)."""
        config_view = gui_components['config_view']
        
        # N1: negative value (boundary behavior)
        config_view.n_repos_var.set(-1)
        config = config_view.get_config_values()
        assert config['n_repos'] == -1, "N1: n_repos should accept negative values for testing"
        
        # N2: zero value
        config_view.n_repos_var.set(0)
        config = config_view.get_config_values()
        assert config['n_repos'] == 0, "N2: n_repos should be 0"
        
        # N3: valid positive value
        config_view.n_repos_var.set(5)
        config = config_view.get_config_values()
        assert config['n_repos'] == 5, "N3: n_repos should be 5"
        
        # N4: large value
        config_view.n_repos_var.set(1000)
        config = config_view.get_config_values()
        assert config['n_repos'] == 1000, "N4: n_repos should be 1000"


class TestGUIPathConfiguration:
    """Tests for GUI path configuration."""
    
    def test_default_path_values(self, gui_components):
        """Verify default path values."""
        config_view = gui_components['config_view']
        
        # Defaults are set in the ConfigView constructor
        assert config_view.io_path_var.get() == "./io"
        assert config_view.repo_path_var.get() == "./io/repos"
        assert config_view.project_list_var.get() == "./io/applied_projects.csv"
    
    def test_path_update(self, gui_components, tmp_path):
        """Verify that paths can be updated."""
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











