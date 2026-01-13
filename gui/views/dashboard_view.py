# C:\ISTA_Progetti\MARK-2.0-Plus\gui\views\dashboard_view.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from typing import Callable, Dict

class DashboardView:
    def __init__(self, parent):
        self.parent = parent
        self.callbacks: Dict[str, Callable] = {}

        self.container = ttk.Frame(parent)
        self.container.pack(fill="both", expand=True)

        self.container.columnconfigure(0, weight=1)
        self.container.columnconfigure(1, weight=3)

        # LEFT – analysis list
        self.tree = ttk.Treeview(self.container, show="tree")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # RIGHT – main panel
        self.right_panel = ttk.Frame(self.container)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right_panel.columnconfigure(0, weight=1)

        # --- Summary ---
        self.summary = ttk.LabelFrame(self.right_panel, text="Classification Summary", padding=10)
        self.summary.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        self.summary_labels = {}
        for key in ("Producer", "Consumer", "Producer & Consumer"):
            lbl = ttk.Label(self.summary, text=f"{key}: 0", font=("Segoe UI", 11))
            lbl.pack(anchor="w", pady=4)
            self.summary_labels[key] = lbl

        # --- Metrics ---
        self.metrics_frame = ttk.LabelFrame(self.right_panel, text="Code Metrics", padding=10)
        self.metrics_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        self.metrics_labels = {}
        for key in ("Media Complexity Cyclomatic", "Media Maintainability Index"):
            lbl = ttk.Label(self.metrics_frame, text=f"{key}: 0", font=("Segoe UI", 11))
            lbl.pack(anchor="w", pady=4)
            self.metrics_labels[key] = lbl

        # --- Keywords ---
        self.libs_frame = ttk.LabelFrame(self.right_panel, text="ML Keywords Usage", padding=10)
        self.libs_frame.grid(row=2, column=0, sticky="nsew")
        
        self.libs_frame.columnconfigure(0, weight=1)
        self.libs_tree = ttk.Treeview(
            self.libs_frame, 
            columns=("library", "keyword", "occurrences"), 
            show="headings",
            height=10)
        
        self.libs_tree.heading("library", text="Library")
        self.libs_tree.heading("keyword", text="Keyword")
        self.libs_tree.heading("occurrences", text="Occurrences")
        
        self.libs_tree.column("library", width=120)
        self.libs_tree.column("keyword", width=150)
        self.libs_tree.column("occurrences", width=80, anchor="center")

        self.libs_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.libs_frame, orient="vertical", command=self.libs_tree.yview)
        self.libs_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    # --- Callbacks ---
    def register_callback(self, name: str, fn: Callable):
        self.callbacks[name] = fn

    # --- Popola la lista di analisi ---
    def populate_analyses(self, analysis_ids):
        self.tree.delete(*self.tree.get_children())
        for x in analysis_ids:
            self.tree.insert("", "end", iid=x, text=f"Analysis_{x}")

    # --- Aggiorna Summary ---
    def update_summary(self, data: Dict[str, int]):
        for key, value in data.items():
            if key in self.summary_labels:  # evita KeyError
                self.summary_labels[key].configure(text=f"{key}: {value}")

    # --- Aggiorna Metrics ---
    def update_metrics(self, data: Dict[str, float]):
        for key, value in data.items():
            if key in self.metrics_labels:  # evita KeyError
                self.metrics_labels[key].configure(text=f"{key}: {value}")

    # --- Evento selezione analisi ---
    def _on_select(self, _):
        sel = self.tree.selection()
        if sel and "on_analysis_select" in self.callbacks:
            self.callbacks["on_analysis_select"](sel[0])

    # --- Update Keywords ---
    def update_library(self, data: list):
        """Update the keywords table.
        
        Args:
            data: List of tuples (library, keyword, occurrences) sorted by occurrences descending
        """
        # Clear table
        for row in self.libs_tree.get_children():
            self.libs_tree.delete(row)

        # Data is already sorted by occurrences (descending)
        for library, keyword, occurrences in data:
            self.libs_tree.insert("", "end", values=(library, keyword, occurrences))

