# Command to run tests: pytest -vv -s test/system_test_dashboard/dashboard_test.py
"""Black-box system testing for MARK 2.0 Dashboard interface.

HOW TO DISABLE DEBUG PRINTS:
To disable all debug print statements, modify the debug() function (around line 80):
- Comment out the print(msg) line
- Uncomment the pass statement
Example:
    def debug(msg):
        #print(msg)
        pass  # <-- use this instead of print to disable all debug output

Test Frame (TF) for validating MARK 2.0 Plus Dashboard.
Run with command: pytest -v test/system_test_dashboard/dashboard_test.py

Categories and constraints tested:
- DPC0/DPC1: Directory producer e consumer (empty/non-empty)
- DM0/DM1: Directory metrics (empty/non-empty)

Test Frames:
- TF1: DPC0 + DM0 → No analysis available
- TF2: DPC0 + DM1 → Analysis with metrics only (producer/consumer counts = 0)
- TF3: DPC1 + DM0 → Analysis with producer/consumer data only (metrics = 0)
- TF4: DPC1 + DM1 → Full analysis with all data
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
def temp_output_structure(tmp_path):
    """Setup temporary output structure with empty directories.
    
    Creates the standard output directory structure:
    - output/producer/
    - output/consumer/
    - output/metrics/
    """
    output_path = tmp_path / "output"
    output_path.mkdir()
    
    # Create empty output directories
    (output_path / "producer").mkdir(parents=True)
    (output_path / "consumer").mkdir(parents=True)
    (output_path / "metrics").mkdir(parents=True)
    
    return output_path


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


# ===== DEBUG HELPER (comment this function to disable all print statements) =====
def debug(msg):
    print(msg)
    #pass  # <-- use this instead of print to disable all output


@pytest.fixture
def dashboard_components(tk_root, temp_output_structure):
    """Setup Dashboard GUI components for testing."""
    from gui.main_window import MainWindow
    from gui.controller import AppController
    from gui.services.output_reader import OutputReader
    
    # Create output reader with temporary path
    output_reader = OutputReader(temp_output_structure)
    
    # Create main window
    main_window = MainWindow(tk_root)
    
    # Create controller
    controller = AppController(main_window=main_window, output_reader=output_reader)
    
    return {
        'root': tk_root,
        'main_window': main_window,
        'controller': controller,
        'dashboard_view': main_window.get_dashboard_view(),
        'output_reader': output_reader,
        'output_path': temp_output_structure
    }


def create_producer_results(output_path: Path, analysis_id: str, data: list):
    """Create a producer results.csv file with the given data.
    
    Args:
        output_path: Base output directory path
        analysis_id: Analysis identifier (e.g., "1", "2")
        data: List of tuples (project_name, is_ml, library, where, keyword, line_number)
    """
    producer_dir = output_path / "producer" / f"producer_{analysis_id}"
    producer_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = producer_dir / "results.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ProjectName', 'Is ML producer', 'libraries', 'where', 'keyword', 'line_number'])
        for row in data:
            writer.writerow(row)
    
    return csv_path


def create_consumer_results(output_path: Path, analysis_id: str, data: list):
    """Create a consumer results.csv file with the given data.
    
    Args:
        output_path: Base output directory path
        analysis_id: Analysis identifier (e.g., "1", "2")
        data: List of tuples (project_name, is_ml, library, where, keyword, line_number)
    """
    consumer_dir = output_path / "consumer" / f"consumer_{analysis_id}"
    consumer_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = consumer_dir / "results.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ProjectName', 'Is ML consumer', 'libraries', 'where', 'keyword', 'line_number'])
        for row in data:
            writer.writerow(row)
    
    return csv_path


def create_metrics_results(output_path: Path, analysis_id: str, data: list):
    """Create a metrics.csv file with the given data.
    
    Args:
        output_path: Base output directory path
        analysis_id: Analysis identifier (e.g., "1", "2")
        data: List of tuples (project_name, cc_avg, mi_avg)
    """
    metrics_dir = output_path / "metrics" / f"metrics_{analysis_id}"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = metrics_dir / "metrics.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ProjectName', 'CC_avg', 'MI_avg'])
        for row in data:
            writer.writerow(row)
    
    return csv_path


def get_summary_label_values(dashboard_view) -> dict:
    """Extract current values from summary labels.
    
    Returns:
        Dictionary with keys 'Producer', 'Consumer', 'Producer & Consumer' 
        and their integer values.
    """
    result = {}
    for key, label in dashboard_view.summary_labels.items():
        text = label.cget("text")
        # Parse "Producer: 5" -> 5
        value = int(text.split(": ")[1]) if ": " in text else 0
        result[key] = value
    return result


def get_metrics_label_values(dashboard_view) -> dict:
    """Extract current values from metrics labels.
    
    Returns:
        Dictionary with metric names and their float values.
    """
    result = {}
    for key, label in dashboard_view.metrics_labels.items():
        text = label.cget("text")
        # Parse "Media Complexity Cyclomatic: 3.5" -> 3.5
        value = float(text.split(": ")[1]) if ": " in text else 0.0
        result[key] = value
    return result


def get_keywords_table_data(dashboard_view) -> list:
    """Extract data from keywords treeview table.
    
    Returns:
        List of tuples (library, keyword, occurrences).
    """
    data = []
    for item in dashboard_view.libs_tree.get_children():
        values = dashboard_view.libs_tree.item(item)['values']
        if len(values) >= 3:
            data.append((values[0], values[1], values[2]))
    return data


def get_analysis_list(dashboard_view) -> list:
    """Get list of available analyses from the treeview.
    
    Returns:
        List of analysis IDs.
    """
    return list(dashboard_view.tree.get_children())


# ============================================================================
# TEST CLASS - DASHBOARD TEST FRAMES
# ============================================================================


class TestDashboardSystemTestFrames:
    """
    Test Frame for validating MARK 2.0 Plus Dashboard.
    
    Each test frame verifies a specific combination of:
    - Producer/Consumer directory state (empty/non-empty)
    - Metrics directory state (empty/non-empty)
    - Dashboard UI state and displayed values
    """

    # ========================================================================
    # TC1/TF1: DPC0 + DM0 - All directories empty
    # ========================================================================
    def test_TC1_all_directories_empty(self, dashboard_components):
        """
        TC1/TF1: DPC0 + DM0 - All directories empty

        ID: TC1
        Combination: DPC0 + DM0
        Oracle: No analysis available, displays "No analysis selected" message
        
        INPUT:
        - io/output/consumer: empty directory
        - io/output/producer: empty directory
        - io/output/metrics: empty directory
        
        ENVIRONMENT STATE:
        - All output directories exist but contain no analysis results
        - Dashboard is initialized with empty output structure
        
        ACTIONS:
        - Initialize dashboard with empty directories
        - Check available analyses
        - Verify default message is displayed
        
        EXPECTED OUTPUT:
        - No analyses available in the list
        - Default message "No analysis selected" is visible
        - No summary, metrics, or keywords data displayed
        """
        dashboard_view = dashboard_components['dashboard_view']
        controller = dashboard_components['controller']
        output_path = dashboard_components['output_path']
        
        # Precondition DPC0: Producer and Consumer directories are empty
        producer_path = output_path / "producer"
        consumer_path = output_path / "consumer"
        assert producer_path.exists() and len(list(producer_path.iterdir())) == 0, (
            "Precondition DPC0 failed: producer directory is not empty"
        )
        assert consumer_path.exists() and len(list(consumer_path.iterdir())) == 0, (
            "Precondition DPC0 failed: consumer directory is not empty"
        )
        
        # Precondition DM0: Metrics directory is empty
        metrics_path = output_path / "metrics"
        assert metrics_path.exists() and len(list(metrics_path.iterdir())) == 0, (
            "Precondition DM0 failed: metrics directory is not empty"
        )
        
        debug(f"\n[DEBUG] TC1 - Preconditions:")
        debug(f"  DPC0 (producer empty): {len(list(producer_path.iterdir())) == 0}")
        debug(f"  DPC0 (consumer empty): {len(list(consumer_path.iterdir())) == 0}")
        debug(f"  DM0 (metrics empty): {len(list(metrics_path.iterdir())) == 0}")
        
        # Action: Refresh to load analyses
        controller._refresh_output_tree()
        
        # Oracle 1: No analyses available
        analyses = get_analysis_list(dashboard_view)
        
        debug(f"\n[DEBUG] TC1 - Analysis list:")
        debug(f"  Expected: []")
        debug(f"  Actual: {analyses}")
        
        assert len(analyses) == 0, (
            f"TC1 FAILED: Expected no analyses, but found {len(analyses)}\n"
            f"Analyses: {analyses}"
        )
                
        
        # Oracle : Verify "No analysis selected" text is displayed
        # Find the label inside the default_message_frame
        expected_message = "No analysis selected"
        message_found = False
        actual_text = None
        
        for child in dashboard_view.default_message_frame.winfo_children():
            try:
                actual_text = child.cget("text")
                if actual_text == expected_message:
                    message_found = True
                    break
            except Exception:
                continue
        
        debug(f"\n[DEBUG] TC1 - Default message text:")
        debug(f"  Expected: '{expected_message}'")
        debug(f"  Actual: '{actual_text}'")
        
        assert message_found, (
            f"TC1 FAILED: Expected message '{expected_message}' not found\n"
            f"Actual text found: '{actual_text}'"
        )

    # ========================================================================
    # TC2/TF2: DPC0 + DM1 - Only metrics available
    # ========================================================================
    def test_TC2_only_metrics_available(self, dashboard_components):
        """
        TC2/TF2: DPC0 + DM1 - Only metrics available

        ID: TC2
        Combination: DPC0 + DM1
        Oracle: Analysis available with metrics only, producer/consumer counts = 0
        
        INPUT:
        - io/output/consumer: empty directory
        - io/output/producer: empty directory
        - io/output/metrics: contains metrics_1 with real project data:
            - 2knal: CC=4.74, MI=38.84
            - 5hirish: CC=2.8, MI=51.22
            - 921kiyo: CC=2.3, MI=50.41
            - aaronlam88: CC=2.3, MI=64.56
        
        ENVIRONMENT STATE:
        - Producer and consumer directories are empty
        - Metrics directory contains analysis results for 4 projects
        
        ACTIONS:
        - Create metrics data in output/metrics/metrics_1/
        - Refresh dashboard
        - Select analysis "1"
        - Verify displayed values
        
        EXPECTED OUTPUT:
        - Analysis "1" appears in list
        - Summary shows: Producer=0, Consumer=0, Producer & Consumer=0
        - Metrics shows: 
            - Media Complexity C .04
            - Media Maintainability Index = (38.84+51.22+50.41+64.56)/4 = 51.26
        - Keywords table is empty (no producer/consumer data)
        """
        dashboard_view = dashboard_components['dashboard_view']
        controller = dashboard_components['controller']
        output_path = dashboard_components['output_path']
        
        # Setup DM1: Create metrics data with real values
        metrics_data = [
            ('2knal', 4.74, 38.84),
            ('5hirish', 2.8, 51.22),
            ('921kiyo', 2.3, 50.41),
            ('aaronlam88', 2.3, 64.56)
        ]
        create_metrics_results(output_path, "1", metrics_data)
        
        # Verify precondition DPC0: Producer and Consumer are empty
        producer_path = output_path / "producer"
        consumer_path = output_path / "consumer"
        assert len(list(producer_path.iterdir())) == 0, (
            "Precondition DPC0 failed: producer directory is not empty"
        )
        assert len(list(consumer_path.iterdir())) == 0, (
            "Precondition DPC0 failed: consumer directory is not empty"
        )
        
        # Verify precondition DM1: Metrics directory has data
        metrics_path = output_path / "metrics"
        assert len(list(metrics_path.iterdir())) > 0, (
            "Precondition DM1 failed: metrics directory is empty"
        )
        
        debug(f"\n[DEBUG] TC2 - Preconditions:")
        debug(f"  DPC0 (producer empty): {len(list(producer_path.iterdir())) == 0}")
        debug(f"  DPC0 (consumer empty): {len(list(consumer_path.iterdir())) == 0}")
        debug(f"  DM1 (metrics has data): {len(list(metrics_path.iterdir())) > 0}")
        
        # Action: Refresh to load analyses
        controller._refresh_output_tree()
        
        # Oracle 1: Analysis "1" is available
        analyses = get_analysis_list(dashboard_view)
        
        debug(f"\n[DEBUG] TC2 - Analysis list:")
        debug(f"  Expected: ['1']")
        debug(f"  Actual: {analyses}")
        
        assert "1" in analyses, (
            f"TC2 FAILED: Expected analysis '1' in list\n"
            f"Available analyses: {analyses}"
        )
        
        # Action: Select analysis "1"
        dashboard_view.tree.selection_set("1")
        dashboard_view.tree.event_generate("<<TreeviewSelect>>")
        controller._on_analysis_select("1")
        
        # Oracle 2: Summary shows all zeros
        summary_values = get_summary_label_values(dashboard_view)
        expected_summary = {"Producer": 0, "Consumer": 0, "Producer & Consumer": 0}
        
        debug(f"\n[DEBUG] TC2 - Summary values:")
        debug(f"  Expected: {expected_summary}")
        debug(f"  Actual: {summary_values}")
        
        assert summary_values == expected_summary, (
            f"TC2 FAILED: Summary values mismatch\n"
            f"Expected: {expected_summary}\n"
            f"Actual: {summary_values}"
        )
        
        # Oracle 3: Metrics shows calculated averages
        # Expected: CC_avg = (4.74+2.8+2.3+2.3)/4 = 3.035 -> 3.04
        # Expected: MI_avg = (38.84+51.22+50.41+64.56)/4 = 51.2575 -> 51.26
        metrics_values = get_metrics_label_values(dashboard_view)
        expected_cc = round((4.74 + 2.8 + 2.3 + 2.3) / 4, 2)  # 3.04
        expected_mi = round((38.84 + 51.22 + 50.41 + 64.56) / 4, 2)  # 51.26
        
        debug(f"\n[DEBUG] TC2 - Metrics values:")
        debug(f"  Expected CC: {expected_cc}")
        debug(f"  Actual CC: {metrics_values.get('Media Complexity Cyclomatic', 0)}")
        debug(f"  Expected MI: {expected_mi}")
        debug(f"  Actual MI: {metrics_values.get('Media Maintainability Index', 0)}")
        
        assert metrics_values["Media Complexity Cyclomatic"] == expected_cc, (
            f"TC2 FAILED: Cyclomatic Complexity mismatch\n"
            f"Expected: {expected_cc}, Actual: {metrics_values['Media Complexity Cyclomatic']}"
        )
        assert metrics_values["Media Maintainability Index"] == expected_mi, (
            f"TC2 FAILED: Maintainability Index mismatch\n"
            f"Expected: {expected_mi}, Actual: {metrics_values['Media Maintainability Index']}"
        )
        
        # Oracle 4: Keywords table is empty
        keywords_data = get_keywords_table_data(dashboard_view)
        
        debug(f"\n[DEBUG] TC2 - Keywords table:")
        debug(f"  Expected: [] (empty)")
        debug(f"  Actual: {keywords_data}")
        
        assert len(keywords_data) == 0, (
            f"TC2 FAILED: Keywords table should be empty\n"
            f"Found: {keywords_data}"
        )
        
        debug(f"\nTC2 PASSED:")
        debug(f"  - Analysis '1' available")
        debug(f"  - Summary: Producer=0, Consumer=0, Producer & Consumer=0")
        debug(f"  - Metrics: CC={expected_cc}, MI={expected_mi}")
        debug(f"  - Keywords: empty")

    # ========================================================================
    # TC3/TF3: DPC1 + DM0 - Only producer/consumer available
    # ========================================================================
    def test_TC3_only_producer_consumer_available(self, dashboard_components):
        """
        TC3/TF3: DPC1 + DM0 - Only producer/consumer available

        ID: TC3
        Combination: DPC1 + DM0
        Oracle: Analysis available with producer/consumer data only, metrics = 0
        
        INPUT:
        - io/output/producer: contains producer_1 with real data:
            - 5hirish/adam_qas: sklearn, .fit(
            - 921kiyo/3d-dl: keras, .fit_generator(
            - 921kiyo/3d-dl: tensorflow, .train.
            - aaronlam88/cmpe295: sklearn, .fit(
        - io/output/consumer: contains consumer_1 with real data:
            - 921kiyo/3d-dl: keras, .predict(
        - io/output/metrics: empty directory
        
        ENVIRONMENT STATE:
        - Producer has 4 rows (2 unique projects: 5hirish/adam_qas, 921kiyo/3d-dl, aaronlam88/cmpe295)
        - Consumer has 1 row (1 unique project: 921kiyo/3d-dl)
        - 921kiyo/3d-dl is both producer AND consumer
        
        ACTIONS:
        - Create producer and consumer data
        - Refresh dashboard
        - Select analysis "1"
        - Verify displayed values
        
        EXPECTED OUTPUT:
        - Summary shows: Producer=3, Consumer=1, Producer & Consumer=1
        - Metrics shows: CC=0, MI=0
        - Keywords shows top keywords:
            - sklearn, .fit( -> 2 occurrences
            - keras, .fit_generator( -> 1 occurrence
            - tensorflow, .train. -> 1 occurrence
            - keras, .predict( -> 1 occurrence
        """
        dashboard_view = dashboard_components['dashboard_view']
        controller = dashboard_components['controller']
        output_path = dashboard_components['output_path']
        
        # Setup DPC1: Create producer data with real values
        producer_data = [
            ('5hirish/adam_qas', 'Yes', 'sklearn', 'io/repos/5hirish/adam_qas/classifier.py', '.fit(', 68),
            ('5hirish/adam_qas', 'Yes', 'sklearn', 'io/repos/5hirish/adam_qas/trainer.py', '.fit(', 44),
            ('921kiyo/3d-dl', 'Yes', 'keras', 'io/repos/921kiyo/3d-dl/train.py', '.fit_generator(', 336),
            ('921kiyo/3d-dl', 'Yes', 'tensorflow', 'io/repos/921kiyo/3d-dl/pipeline.py', '.train.', 37),
            ('aaronlam88/cmpe295', 'Yes', 'sklearn', 'io/repos/aaronlam88/cmpe295/classifier.py', '.fit(', 40)
        ]
        create_producer_results(output_path, "1", producer_data)
        
        # Setup DPC1: Create consumer data
        consumer_data = [
            ('921kiyo/3d-dl', 'Yes', 'keras', 'io/repos/921kiyo/3d-dl/flask_app.py', '.predict(', 82)
        ]
        create_consumer_results(output_path, "1", consumer_data)
        
        # Verify precondition DPC1: Producer and Consumer have data
        producer_path = output_path / "producer"
        consumer_path = output_path / "consumer"
        assert len(list(producer_path.iterdir())) > 0, (
            "Precondition DPC1 failed: producer directory is empty"
        )
        assert len(list(consumer_path.iterdir())) > 0, (
            "Precondition DPC1 failed: consumer directory is empty"
        )
        
        # Verify precondition DM0: Metrics is empty
        metrics_path = output_path / "metrics"
        assert len(list(metrics_path.iterdir())) == 0, (
            "Precondition DM0 failed: metrics directory is not empty"
        )
        
        debug(f"\n[DEBUG] TC3 - Preconditions:")
        debug(f"  DPC1 (producer has data): {len(list(producer_path.iterdir())) > 0}")
        debug(f"  DPC1 (consumer has data): {len(list(consumer_path.iterdir())) > 0}")
        debug(f"  DM0 (metrics empty): {len(list(metrics_path.iterdir())) == 0}")
        
        # Action: Refresh to load analyses
        controller._refresh_output_tree()
        
        # Oracle 1: Analysis "1" is available
        analyses = get_analysis_list(dashboard_view)
        assert "1" in analyses, (
            f"TC3 FAILED: Expected analysis '1' in list\n"
            f"Available analyses: {analyses}"
        )
        
        # Action: Select analysis "1"
        dashboard_view.tree.selection_set("1")
        dashboard_view.tree.event_generate("<<TreeviewSelect>>")
        controller._on_analysis_select("1")
        
        # Oracle 2: Summary shows correct counts
        # Producer unique projects: 5hirish/adam_qas, 921kiyo/3d-dl, aaronlam88/cmpe295 = 3
        # Consumer unique projects: 921kiyo/3d-dl = 1
        # Producer & Consumer: 921kiyo/3d-dl = 1
        summary_values = get_summary_label_values(dashboard_view)
        expected_summary = {"Producer": 3, "Consumer": 1, "Producer & Consumer": 1}
        
        debug(f"\n[DEBUG] TC3 - Summary values:")
        debug(f"  Expected: {expected_summary}")
        debug(f"  Actual: {summary_values}")
        
        assert summary_values == expected_summary, (
            f"TC3 FAILED: Summary values mismatch\n"
            f"Expected: {expected_summary}\n"
            f"Actual: {summary_values}"
        )
        
        # Oracle 3: Metrics shows zeros
        metrics_values = get_metrics_label_values(dashboard_view)
        
        debug(f"\n[DEBUG] TC3 - Metrics values:")
        debug(f"  Expected CC: 0")
        debug(f"  Actual CC: {metrics_values.get('Media Complexity Cyclomatic', 0)}")
        debug(f"  Expected MI: 0")
        debug(f"  Actual MI: {metrics_values.get('Media Maintainability Index', 0)}")
        
        assert metrics_values["Media Complexity Cyclomatic"] == 0, (
            f"TC3 FAILED: Cyclomatic Complexity should be 0\n"
            f"Actual: {metrics_values['Media Complexity Cyclomatic']}"
        )
        assert metrics_values["Media Maintainability Index"] == 0, (
            f"TC3 FAILED: Maintainability Index should be 0\n"
            f"Actual: {metrics_values['Media Maintainability Index']}"
        )
        
        # Oracle 4: Keywords table shows top keywords with exact values
        # Expected keywords from data:
        # sklearn, .fit( -> 3 occurrences (2 from producer 5hirish + 1 from aaronlam88)
        # keras, .fit_generator( -> 1 occurrence
        # tensorflow, .train. -> 1 occurrence
        # keras, .predict( -> 1 occurrence
        keywords_data = get_keywords_table_data(dashboard_view)
        
        debug(f"\n[DEBUG] TC3 - Keywords table:")
        debug(f"  Data found: {keywords_data}")
        
        # Expected exact keywords table
        expected_keywords = [
            ('sklearn', '.fit(', 3),
            ('keras', '.fit_generator(', 1),
            ('keras', '.predict(', 1),
            ('tensorflow', '.train.', 1)
        ]
        
        assert len(keywords_data) == len(expected_keywords), (
            f"TC3 FAILED: Keywords table should have {len(expected_keywords)} entries\n"
            f"Expected: {expected_keywords}\n"
            f"Actual: {keywords_data}"
        )
        
        # Verify each expected keyword is present with correct count
        for lib, kw, expected_count in expected_keywords:
            found = False
            actual_count = 0
            for data_lib, data_kw, data_count in keywords_data:
                if data_lib == lib and data_kw == kw:
                    found = True
                    actual_count = data_count
                    break
            
            assert found, (
                f"TC3 FAILED: Expected keyword '{lib}, {kw}' not found\n"
                f"Keywords: {keywords_data}"
            )
            assert actual_count == expected_count, (
                f"TC3 FAILED: Keyword '{lib}, {kw}' count mismatch\n"
                f"Expected: {expected_count}, Actual: {actual_count}"
            )
        
        debug(f"\nTC3 PASSED:")
        debug(f"  - Analysis '1' available")
        debug(f"  - Summary: Producer=3, Consumer=1, Producer & Consumer=1")
        debug(f"  - Metrics: CC=0, MI=0")
        debug(f"  - Keywords table matches expected values")

    # ========================================================================
    # TC4/TF4: DPC1 + DM1 - All data available
    # ========================================================================
    def test_TC4_all_data_available(self, dashboard_components):
        """
        TC4/TF4: DPC1 + DM1 - All data available

        ID: TC4
        Combination: DPC1 + DM1
        Oracle: Full analysis with producer/consumer counts, metrics, and keywords
        
        INPUT:
        - io/output/producer: contains producer_1 with real data:
            - 5hirish/adam_qas: sklearn, .fit(
            - 921kiyo/3d-dl: keras, .fit_generator(
            - 921kiyo/3d-dl: tensorflow, .train.
            - abojchevski/graph2gauss: tensorflow, .train.
        - io/output/consumer: contains consumer_1 with real data:
            - 921kiyo/3d-dl: keras, .predict(
            - abojchevski/graph2gauss: tensorflow, .predict_proba(
        - io/output/metrics: contains metrics_1 with real data:
            - 5hirish: CC=2.8, MI=51.22
            - 921kiyo: CC=2.3, MI=50.41
            - abojchevski: CC=4.38, MI=41.65
        
        ENVIRONMENT STATE:
        - All three output directories contain analysis results
        - Producer: 3 unique projects
        - Consumer: 2 unique projects
        - Both Producer & Consumer: 921kiyo/3d-dl, abojchevski/graph2gauss = 2
        
        ACTIONS:
        - Create producer, consumer, and metrics data
        - Refresh dashboard
        - Select analysis "1"
        - Verify all displayed values
        
        EXPECTED OUTPUT:
        - Summary: Producer=3, Consumer=2, Producer & Consumer=2
        - Metrics: CC=(2.8+2.3+4.38)/3=3.16, MI=(51.22+50.41+41.65)/3=47.76
        - Keywords: top 10 with correct counts
        """
        dashboard_view = dashboard_components['dashboard_view']
        controller = dashboard_components['controller']
        output_path = dashboard_components['output_path']
        
        # Setup DPC1: Create producer data
        producer_data = [
            ('5hirish/adam_qas', 'Yes', 'sklearn', 'io/repos/5hirish/adam_qas/classifier.py', '.fit(', 68),
            ('921kiyo/3d-dl', 'Yes', 'keras', 'io/repos/921kiyo/3d-dl/train.py', '.fit_generator(', 336),
            ('921kiyo/3d-dl', 'Yes', 'tensorflow', 'io/repos/921kiyo/3d-dl/pipeline.py', '.train.', 37),
            ('921kiyo/3d-dl', 'Yes', 'tensorflow', 'io/repos/921kiyo/3d-dl/retrain.py', '.train.', 876),
            ('abojchevski/graph2gauss', 'Yes', 'tensorflow', 'io/repos/abojchevski/graph2gauss/train.py', '.train.', 45)
        ]
        create_producer_results(output_path, "1", producer_data)
        
        # Setup DPC1: Create consumer data
        consumer_data = [
            ('921kiyo/3d-dl', 'Yes', 'keras', 'io/repos/921kiyo/3d-dl/flask_app.py', '.predict(', 82),
            ('921kiyo/3d-dl', 'Yes', 'keras', 'io/repos/921kiyo/3d-dl/classify.py', '.predict(', 53),
            ('abojchevski/graph2gauss', 'Yes', 'tensorflow', 'io/repos/abojchevski/graph2gauss/eval.py', '.predict_proba(', 120)
        ]
        create_consumer_results(output_path, "1", consumer_data)
        
        # Setup DM1: Create metrics data
        metrics_data = [
            ('5hirish', 2.8, 51.22),
            ('921kiyo', 2.3, 50.41),
            ('abojchevski', 4.38, 41.65)
        ]
        create_metrics_results(output_path, "1", metrics_data)
        
        # Verify preconditions
        producer_path = output_path / "producer"
        consumer_path = output_path / "consumer"
        metrics_path = output_path / "metrics"
        
        assert len(list(producer_path.iterdir())) > 0, "DPC1 failed: producer empty"
        assert len(list(consumer_path.iterdir())) > 0, "DPC1 failed: consumer empty"
        assert len(list(metrics_path.iterdir())) > 0, "DM1 failed: metrics empty"
        
        debug(f"\n[DEBUG] TC4 - Preconditions:")
        debug(f"  DPC1 (producer has data): True")
        debug(f"  DPC1 (consumer has data): True")
        debug(f"  DM1 (metrics has data): True")
        
        # Action: Refresh to load analyses
        controller._refresh_output_tree()
        
        # Oracle 1: Analysis "1" is available
        analyses = get_analysis_list(dashboard_view)
        assert "1" in analyses, f"TC4 FAILED: Analysis '1' not in list: {analyses}"
        
        # Action: Select analysis "1"
        dashboard_view.tree.selection_set("1")
        dashboard_view.tree.event_generate("<<TreeviewSelect>>")
        controller._on_analysis_select("1")
        
        # Oracle 2: Summary shows correct counts
        # Producer unique: 5hirish/adam_qas, 921kiyo/3d-dl, abojchevski/graph2gauss = 3
        # Consumer unique: 921kiyo/3d-dl, abojchevski/graph2gauss = 2
        # Both: 921kiyo/3d-dl, abojchevski/graph2gauss = 2
        summary_values = get_summary_label_values(dashboard_view)
        expected_summary = {"Producer": 3, "Consumer": 2, "Producer & Consumer": 2}
        
        debug(f"\n[DEBUG] TC4 - Summary values:")
        debug(f"  Expected: {expected_summary}")
        debug(f"  Actual: {summary_values}")
        
        assert summary_values == expected_summary, (
            f"TC4 FAILED: Summary mismatch\n"
            f"Expected: {expected_summary}\n"
            f"Actual: {summary_values}"
        )
        
        # Oracle 3: Metrics shows calculated averages
        # CC = (2.8 + 2.3 + 4.38) / 3 = 3.16
        # MI = (51.22 + 50.41 + 41.65) / 3 = 47.76
        expected_cc = round((2.8 + 2.3 + 4.38) / 3, 2)
        expected_mi = round((51.22 + 50.41 + 41.65) / 3, 2)
        metrics_values = get_metrics_label_values(dashboard_view)
        
        debug(f"\n[DEBUG] TC4 - Metrics values:")
        debug(f"  Expected CC: {expected_cc}")
        debug(f"  Actual CC: {metrics_values['Media Complexity Cyclomatic']}")
        debug(f"  Expected MI: {expected_mi}")
        debug(f"  Actual MI: {metrics_values['Media Maintainability Index']}")
        
        assert metrics_values["Media Complexity Cyclomatic"] == expected_cc, (
            f"TC4 FAILED: CC mismatch. Expected {expected_cc}, got {metrics_values['Media Complexity Cyclomatic']}"
        )
        assert metrics_values["Media Maintainability Index"] == expected_mi, (
            f"TC4 FAILED: MI mismatch. Expected {expected_mi}, got {metrics_values['Media Maintainability Index']}"
        )
        
        # Oracle 4: Keywords table shows data with exact values
        keywords_data = get_keywords_table_data(dashboard_view)
        
        debug(f"\n[DEBUG] TC4 - Keywords table:")
        debug(f"  Data: {keywords_data}")
        
        # Expected exact keywords table
        expected_keywords = [
            ('tensorflow', '.train.', 3),
            ('keras', '.predict(', 2),
            ('keras', '.fit_generator(', 1),
            ('sklearn', '.fit(', 1),
            ('tensorflow', '.predict_proba(', 1)
        ]
        
        assert len(keywords_data) == len(expected_keywords), (
            f"TC4 FAILED: Keywords table should have {len(expected_keywords)} entries\n"
            f"Expected: {expected_keywords}\n"
            f"Actual: {keywords_data}"
        )
        
        # Verify each expected keyword is present with correct count
        for lib, kw, expected_count in expected_keywords:
            found = False
            actual_count = 0
            for data_lib, data_kw, data_count in keywords_data:
                if data_lib == lib and data_kw == kw:
                    found = True
                    actual_count = data_count
                    break
            
            assert found, (
                f"TC4 FAILED: Expected keyword '{lib}, {kw}' not found\n"
                f"Keywords: {keywords_data}"
            )
            assert actual_count == expected_count, (
                f"TC4 FAILED: Keyword '{lib}, {kw}' count mismatch\n"
                f"Expected: {expected_count}, Actual: {actual_count}"
            )
        
        debug(f"\nTC4 PASSED:")
        debug(f"  - Summary: Producer=3, Consumer=2, Producer & Consumer=2")
        debug(f"  - Metrics: CC={expected_cc}, MI={expected_mi}")
        debug(f"  - Keywords table matches expected values")
