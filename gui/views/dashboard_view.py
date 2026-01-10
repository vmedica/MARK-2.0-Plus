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

        # RIGHT – summary
        self.summary = ttk.Frame(self.container)
        self.summary.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.labels = {}
        for i, key in enumerate(
            ("Producer", "Consumer", "Producer & Consumer", "Non-ML")
        ):
            lbl = ttk.Label(self.summary, text=f"{key}: 0", font=("Segoe UI", 11))
            lbl.pack(anchor="w", pady=4)
            self.labels[key] = lbl

    def register_callback(self, name: str, fn: Callable):
        self.callbacks[name] = fn

    def populate_analyses(self, analysis_ids):
        self.tree.delete(*self.tree.get_children())
        for x in analysis_ids:
            self.tree.insert("", "end", iid=x, text=f"Analysis_{x}")

    def update_summary(self, data: Dict[str, int]):
        for key, value in data.items():
            self.labels[key].configure(text=f"{key}: {value}")

    def _on_select(self, _):
        sel = self.tree.selection()
        if sel and "on_analysis_select" in self.callbacks:
            self.callbacks["on_analysis_select"](sel[0])
