"""Output View - UI for displaying analysis results."""

import tkinter as tk
from pathlib import Path
from typing import List, Dict, Any

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from gui.views.base_view import BaseView
from gui.style import PADDING, FONTS


class OutputView(BaseView):
    """View for displaying analysis output files."""

    def __init__(self, parent):
        super().__init__(parent)
        self.current_file_var = tk.StringVar(value="No file selected")
        self._category_items: Dict[str, str] = {}
        self.create_widgets()

    def create_widgets(self) -> None:
        """Create and layout all output view widgets."""
        self.frame = ttk.Frame(self.parent, padding=PADDING["medium"])

        paned = ttk.PanedWindow(self.frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # Left panel: Directory Tree
        left_frame = ttk.Frame(paned, padding=PADDING["small"])
        paned.add(left_frame, weight=1)

        tree_header = ttk.Frame(left_frame)
        tree_header.pack(fill="x", pady=(0, PADDING["small"]))

        ttk.Label(tree_header, text="Output Files", font=FONTS["heading"]).pack(
            side="left"
        )
        ttk.Button(
            tree_header, text="↻ Refresh", command=self._on_refresh_click, width=10
        ).pack(side="right")

        tree_container = ttk.Frame(left_frame)
        tree_container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            tree_container, selectmode="browse", show="tree headings"
        )
        self.tree.pack(side="left", fill="both", expand=True)

        tree_scroll = ttk.Scrollbar(
            tree_container, orient="vertical", command=self.tree.yview
        )
        tree_scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Right panel: CSV Content
        right_frame = ttk.Frame(paned, padding=PADDING["small"])
        paned.add(right_frame, weight=3)

        ttk.Label(
            right_frame, textvariable=self.current_file_var, font=FONTS["heading"]
        ).pack(anchor="w", pady=(0, PADDING["small"]))

        data_container = ttk.Frame(right_frame)
        data_container.pack(fill="both", expand=True)

        self.data_tree = ttk.Treeview(
            data_container, selectmode="browse", show="headings"
        )
        self.data_tree.pack(side="left", fill="both", expand=True)

        data_scroll_y = ttk.Scrollbar(
            data_container, orient="vertical", command=self.data_tree.yview
        )
        data_scroll_y.pack(side="right", fill="y")
        self.data_tree.configure(yscrollcommand=data_scroll_y.set)

        data_scroll_x = ttk.Scrollbar(
            right_frame, orient="horizontal", command=self.data_tree.xview
        )
        data_scroll_x.pack(fill="x")
        self.data_tree.configure(xscrollcommand=data_scroll_x.set)

        self.data_tree.tag_configure("oddrow", background="#f8f9fa")
        self.data_tree.tag_configure("evenrow", background="#ffffff")

    def _on_tree_select(self, event) -> None:
        """Handle tree item selection."""
        selection = self.tree.selection()
        if not selection:
            return
        item_data = self.tree.item(selection[0])
        if "file" in item_data.get("tags", []):
            file_path = item_data.get("values", [None])[0]
            if file_path:
                self._trigger_callback("on_file_select", Path(file_path))

    def _on_refresh_click(self) -> None:
        """Handle refresh button click."""
        self._trigger_callback("on_refresh")

    def populate_tree(self, tree_data: Dict[str, Any]) -> None:
        """Populate the directory tree with output data."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._category_items.clear()

        categories = {
            "producer": "📦 Producer Analysis",
            "consumer": "👤 Consumer Analysis",
            "metrics": "📊 Metrics Analysis",
        }

        for category, display_name in categories.items():
            dirs = tree_data.get(category, [])
            category_id = self.tree.insert(
                "", "end", text=display_name, open=True, tags=("category",)
            )
            self._category_items[category] = category_id

            for run_dir in dirs:
                run_id = self.tree.insert(
                    category_id,
                    "end",
                    text=f"📁 {run_dir['name']}",
                    open=False,
                    tags=("directory",),
                )
                for file_info in run_dir.get("files", []):
                    icon = "📋" if file_info.get("is_summary") else "📄"
                    self.tree.insert(
                        run_id,
                        "end",
                        text=f"{icon} {file_info['name']}",
                        values=(str(file_info["path"]),),
                        tags=("file",),
                    )

    def display_csv_data(
        self, headers: List[str], rows: List[List[str]], file_name: str
    ) -> None:
        """Display CSV data in the data tree."""
        self.current_file_var.set(f"📄 {file_name}")

        for item in self.data_tree.get_children():
            self.data_tree.delete(item)

        self.data_tree["columns"] = headers

        # Configure columns with fixed widths
        for col in headers:
            self.data_tree.heading(col, text=col, anchor="w")

            # Assign larger widths to important columns
            if col.lower() in ["projectname", "project_name"]:
                width = 300
            elif col.lower() in ["where", "path"]:
                width = 400
            else:
                width = 150

            self.data_tree.column(
                col,
                width=width,
                minwidth=80,
                stretch=False,  # Enable horizontal scrolling
            )

        for i, row in enumerate(rows):
            self.data_tree.insert(
                "", "end", values=row, tags=("oddrow" if i % 2 else "evenrow",)
            )

    def show_loading(self) -> None:
        """Show loading state."""
        self.current_file_var.set("Loading...")

    def show_error(self, message: str) -> None:
        """Show error message."""
        self.current_file_var.set(f"Error: {message}")
