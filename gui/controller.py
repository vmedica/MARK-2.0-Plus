"""Application Controller - Connects views to services."""

import threading
from pathlib import Path
from typing import Optional
from collections import Counter

from gui.services.pipeline_service import (
    PipelineService,
    PipelineConfig,
    PipelineResult,
)
from gui.services.output_reader import OutputReader
from gui.main_window import MainWindow


class AppController:
    """Application controller that connects views to services."""

    def __init__(self, main_window: MainWindow, output_reader: OutputReader):
        self.main_window = main_window
        self.output_reader = output_reader
        self._pipeline_service: Optional[PipelineService] = None
        self._pipeline_thread: Optional[threading.Thread] = None

        self._setup_callbacks()
        self._refresh_output_tree()

    def _setup_callbacks(self) -> None:
        """Register callbacks on all views."""
        config_view = self.main_window.get_config_view()
        config_view.register_callback("on_start_pipeline", self._on_start_pipeline)

        output_view = self.main_window.get_output_view()
        output_view.register_callback("on_file_select", self._on_file_select)
        output_view.register_callback("on_refresh", self._refresh_output_tree)

        dashboard_view = self.main_window.get_dashboard_view()
        dashboard_view.register_callback(
            "on_analysis_select", self._on_analysis_select
        )
        dashboard_view.register_callback("on_refresh", self._refresh_output_tree)

    def _on_start_pipeline(self) -> None:
        """Handle start pipeline request from config view."""
        config_view = self.main_window.get_config_view()
        config_values = config_view.get_config_values()

        # Validate paths
        io_path = config_values["io_path"]
        if not io_path.exists():
            self.main_window.show_error(
                "Invalid Path", f"IO path does not exist: {io_path}"
            )
            return

        # Update output reader to use io_path/output
        self.output_reader.output_path = io_path / "output"

        # Create pipeline configuration
        pipeline_config = PipelineConfig(
            io_path=config_values["io_path"],
            repository_path=config_values["repository_path"],
            project_list_path=config_values["project_list_path"],
            n_repos=config_values["n_repos"],
            run_cloner=config_values["run_cloner"],
            run_cloner_check=config_values["run_cloner_check"],
            run_producer_analysis=config_values["run_producer_analysis"],
            run_consumer_analysis=config_values["run_consumer_analysis"],
            run_metrics_analysis=config_values["run_metrics_analysis"],
            rules_3=config_values["rules_3"],
        )

        self._pipeline_service = PipelineService(pipeline_config)
        config_view.set_running_state(True)

        # Start pipeline in background thread
        self._pipeline_thread = threading.Thread(
            target=self._run_pipeline_thread, daemon=True
        )
        self._pipeline_thread.start()

        # Start polling for completion
        self._poll_completion()

    def _run_pipeline_thread(self) -> None:
        """Run the pipeline in a background thread."""
        try:
            self._result = self._pipeline_service.run_pipeline()
        except Exception as e:
            self._result = PipelineResult(success=False, error_message=str(e))

    def _poll_completion(self) -> None:
        """Poll for pipeline completion."""
        if self._pipeline_thread and self._pipeline_thread.is_alive():
            self.main_window.schedule(100, self._poll_completion)
        else:
            self._on_pipeline_complete()

    def _on_pipeline_complete(self) -> None:
        """Handle pipeline completion."""
        config_view = self.main_window.get_config_view()
        config_view.set_running_state(False)

        result = getattr(self, "_result", None)
        if result and result.success:
            self.main_window.show_info(
                "Success",
                "Pipeline completed successfully!",
            )
            self._refresh_output_tree()
            self.main_window.switch_to_output_tab()
        elif result:
            self.main_window.show_error(
                "Pipeline Failed", f"Error: {result.error_message}"
            )
        else:
            self.main_window.show_error("Error", "Unknown error occurred")

    def _refresh_output_tree(self) -> None:
        """Refresh the output directory tree."""
        output_view = self.main_window.get_output_view() 
        
        dashboard = self.main_window.get_dashboard_view()
        analyses = self.output_reader.find_complete_analyses()
        dashboard.populate_analyses(analyses)
        
        try:
            tree = self.output_reader.scan_output_tree()
            tree_data = self._convert_tree_to_dict(tree)
            output_view.populate_tree(tree_data)
        except Exception as e:
            output_view.show_error(f"Failed to scan output directory: {e}")

       

    def _convert_tree_to_dict(self, tree) -> dict:
        """Convert OutputTree to dictionary format expected by view."""
        result = {}
        for category in ("producer", "consumer", "metrics"):
            dirs = getattr(tree, f"{category}_dirs", [])
            result[category] = []
            for output_dir in dirs:
                dir_data = {
                    "name": output_dir.name,
                    "files": [
                        {"name": f.name, "path": f.path, "is_summary": f.is_summary}
                        for f in output_dir.files
                    ],
                }
                result[category].append(dir_data)
        return result

    def _on_file_select(self, file_path: Path) -> None:
        """Handle file selection in output tree."""
        output_view = self.main_window.get_output_view()
        output_view.show_loading()
        try:
            csv_data = self.output_reader.load_csv(file_path)
            output_view.display_csv_data(
                headers=csv_data.headers, rows=csv_data.rows, file_name=file_path.name
            )
        except Exception as e:
            output_view.show_error(str(e))
    

    def _on_analysis_select(self, analysis_id: str):
        base = self.output_reader.output_path

        # --- Number of Producer / Consumer ---
        prod_csv = base / "producer" / f"producer_{analysis_id}" / "results.csv"
        cons_csv = base / "consumer" / f"consumer_{analysis_id}" / "results.csv"

        # Load CSV files, use empty lists if files don't exist
        try:
            producer_rows = self.output_reader.load_csv(prod_csv).rows
        except FileNotFoundError:
            producer_rows = []
        
        try:
            consumer_rows = self.output_reader.load_csv(cons_csv).rows
        except FileNotFoundError:
            consumer_rows = []

        prod_set = {r[0] for r in producer_rows if len(r) > 0}
        cons_set = {r[0] for r in consumer_rows if len(r) > 0}

        summary = {
            "Producer": len(prod_set),
            "Consumer": len(cons_set),
            "Producer & Consumer": len(prod_set & cons_set)
        }

        # Aggiorna le label del Summary
        self.main_window.get_dashboard_view().update_summary(summary)

        # --- Metrics ---
        metrics_csv = base / "metrics" / f"metrics_{analysis_id}" / "metrics.csv"
        try:
            metrics_rows = self.output_reader.load_csv(metrics_csv).rows

            # Calcolo media per ogni colonna numerica
            cc_values = [float(r[1]) for r in metrics_rows if len(r) > 2]  # Complexity Cyclomatic
            mi_values = [float(r[2]) for r in metrics_rows if len(r) > 2]  # Maintainability Index

            metrics_summary = {
                "Media Complexity Cyclomatic": round(sum(cc_values)/len(cc_values), 2) if cc_values else 0,
                "Media Maintainability Index": round(sum(mi_values)/len(mi_values), 2) if mi_values else 0
            }

            # Aggiorna le label delle metriche
            self.main_window.get_dashboard_view().update_metrics(metrics_summary)

        except FileNotFoundError:
            # Se il CSV delle metriche non esiste
            metrics_summary = {
                "Media Complexity Cyclomatic": 0,
                "Media Maintainability Index": 0
            }
            self.main_window.get_dashboard_view().update_metrics(metrics_summary)
        except Exception as e:
            self.main_window.show_error("Metrics Error", f"Errore nel calcolo delle metriche: {e}")

        # --- Keywords ---
        # Extract (library, keyword) pairs from both producer and consumer
        # CSV columns: ProjectName(0), Is ML(1), libraries(2), where(3), keyword(4), line_number(5)
        keyword_pairs = []
        for r in producer_rows:
            if len(r) > 4:
                keyword_pairs.append((r[2], r[4]))  # (library, keyword)
        for r in consumer_rows:
            if len(r) > 4:
                keyword_pairs.append((r[2], r[4]))  # (library, keyword)

        # Count occurrences of each (library, keyword) pair
        keyword_count = Counter(keyword_pairs)

        # Sort by occurrences (descending) and take top 10
        top10_keywords = sorted(keyword_count.items(), key=lambda x: (-x[1], x[0][0], x[0][1]))[:10]
        
        # Convert to list of tuples (library, keyword, occurrences)
        keyword_data = [(lib, kw, count) for (lib, kw), count in top10_keywords]
        self.main_window.get_dashboard_view().update_library(keyword_data)

