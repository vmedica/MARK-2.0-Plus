"""Configuration View - UI for pipeline configuration."""

import tkinter as tk
from tkinter import filedialog
from pathlib import Path

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
except ImportError:
    import tkinter.ttk as ttk

from gui.views.base_view import BaseView
from gui.style import PADDING, FONTS


class ConfigView(BaseView):
    """View for configuring pipeline parameters."""

    def __init__(self, parent):
        super().__init__(parent)

        # StringVars for path entries
        self.io_path_var = tk.StringVar(value="./io")
        self.repo_path_var = tk.StringVar(value="./io/repos")
        self.project_list_var = tk.StringVar(value="./io/applied_projects.csv")

        # IntVar for n_repos
        self.n_repos_var = tk.IntVar(value=10)

        # BooleanVars for step toggles
        self.run_cloner_var = tk.BooleanVar(value=True)
        self.run_cloner_check_var = tk.BooleanVar(value=True)
        self.run_producer_var = tk.BooleanVar(value=True)
        self.run_consumer_var = tk.BooleanVar(value=True)
        self.run_metrics_var = tk.BooleanVar(value=True)

        # BooleanVar for rules_3
        self.rules_3_var = tk.BooleanVar(value=True)

        self.create_widgets()

    def create_widgets(self) -> None:
        """Create and layout all configuration widgets."""
        self.frame = ttk.Frame(self.parent, padding=PADDING["large"])

        # === PATH CONFIGURATION SECTION ===
        path_frame = ttk.LabelFrame(
            self.frame, text="Path Configuration", padding=PADDING["medium"]
        )
        path_frame.pack(fill="x", pady=(0, PADDING["medium"]))

        # IO Path
        self._create_path_row(
            path_frame, "IO Path:", self.io_path_var, self._on_browse_io_path, row=0
        )

        # Repository Path
        self._create_path_row(
            path_frame,
            "Repository Path:",
            self.repo_path_var,
            self._on_browse_repo_path,
            row=1,
        )

        # Project List Path
        self._create_path_row(
            path_frame,
            "Project List (CSV):",
            self.project_list_var,
            self._on_browse_project_list,
            row=2,
            is_file=True,
        )

        # Configure grid columns
        path_frame.columnconfigure(1, weight=1)

        # === ANALYSIS SETTINGS SECTION ===
        settings_frame = ttk.LabelFrame(
            self.frame, text="Analysis Settings", padding=PADDING["medium"]
        )
        settings_frame.pack(fill="x", pady=(0, PADDING["medium"]))

        # N Repos
        n_repos_frame = ttk.Frame(settings_frame)
        n_repos_frame.pack(fill="x", pady=(0, PADDING["small"]))

        ttk.Label(n_repos_frame, text="Number of Repositories:").pack(side="left")
        ttk.Spinbox(
            n_repos_frame, from_=1, to=1000, textvariable=self.n_repos_var, width=10
        ).pack(side="left", padx=(PADDING["small"], 0))

        # Rules 3 option
        ttk.Checkbutton(
            settings_frame,
            text="Enable Rules 3 (Consumer Analysis)",
            variable=self.rules_3_var,
        ).pack(anchor="w")

        # === PIPELINE STEPS SECTION ===
        steps_frame = ttk.LabelFrame(
            self.frame, text="Pipeline Steps", padding=PADDING["medium"]
        )
        steps_frame.pack(fill="x", pady=(0, PADDING["medium"]))

        # Step checkboxes in a grid
        steps = [
            ("Clone Repositories", self.run_cloner_var),
            ("Verify Cloning", self.run_cloner_check_var),
            ("Producer Analysis", self.run_producer_var),
            ("Consumer Analysis", self.run_consumer_var),
            ("Metrics Analysis", self.run_metrics_var),
        ]

        for i, (label, var) in enumerate(steps):
            cb = ttk.Checkbutton(steps_frame, text=label, variable=var)
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=PADDING["small"])

        # === CONTROL BUTTONS ===
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x")

        self.start_button = ttk.Button(
            button_frame,
            text="Start Analysis",
            command=self._on_start_click,
            bootstyle="success" if hasattr(ttk, "Window") else None,
        )
        self.start_button.pack(side="right")

    def _create_path_row(
        self,
        parent,
        label: str,
        variable: tk.StringVar,
        browse_command,
        row: int,
        is_file: bool = False,
    ) -> None:
        """Create a path input row with label, entry, and browse button."""
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", pady=PADDING["small"]
        )

        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING["small"], pady=PADDING["small"]
        )

        ttk.Button(parent, text="Browse...", command=browse_command, width=10).grid(
            row=row, column=2, pady=PADDING["small"]
        )

    def _on_browse_io_path(self) -> None:
        """Handle IO path browse button click."""
        path = filedialog.askdirectory(
            title="Select IO Directory", initialdir=self.io_path_var.get() or "."
        )
        if path:
            self.io_path_var.set(path)
            # self.repo_path_var.set(str(Path(path) / "repos"))
            # self.project_list_var.set(str(Path(path) / "applied_projects.csv"))

    def _on_browse_repo_path(self) -> None:
        """Handle repository path browse button click."""
        path = filedialog.askdirectory(
            title="Select Repository Directory",
            initialdir=self.repo_path_var.get() or ".",
        )
        if path:
            self.repo_path_var.set(path)

    def _on_browse_project_list(self) -> None:
        """Handle project list browse button click."""
        path = filedialog.askopenfilename(
            title="Select Project List CSV",
            initialdir=str(Path(self.project_list_var.get()).parent) or ".",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if path:
            self.project_list_var.set(path)

    def _on_start_click(self) -> None:
        """Handle start button click."""
        self._trigger_callback("on_start_pipeline")

    def get_config_values(self) -> dict:
        """Get all current configuration values."""
        return {
            "io_path": Path(self.io_path_var.get()),
            "repository_path": Path(self.repo_path_var.get()),
            "project_list_path": Path(self.project_list_var.get()),
            "n_repos": self.n_repos_var.get(),
            "run_cloner": self.run_cloner_var.get(),
            "run_cloner_check": self.run_cloner_check_var.get(),
            "run_producer_analysis": self.run_producer_var.get(),
            "run_consumer_analysis": self.run_consumer_var.get(),
            "run_metrics_analysis": self.run_metrics_var.get(),
            "rules_3": self.rules_3_var.get(),
        }

    def set_running_state(self, is_running: bool) -> None:
        """Update UI to reflect running/idle state."""
        self.start_button.configure(state="disabled" if is_running else "normal")
