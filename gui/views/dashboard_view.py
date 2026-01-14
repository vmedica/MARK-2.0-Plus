"""Dashboard View - UI for displaying analysis summary and metrics."""

import tkinter as tk
from typing import Dict

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from gui.views.base_view import BaseView
from gui.style import PADDING, FONTS


class DashboardView(BaseView):
    """View for displaying analysis dashboard with summary, metrics, and charts."""

    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()

    def create_widgets(self) -> None:
        """Create and layout all dashboard widgets."""
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill="both", expand=True)

        # Configure grid layout: left panel (1) and right panel (3) weight ratio
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=3)
        self.frame.rowconfigure(0, weight=1)

        # Create left and right panels
        self._create_left_panel()
        self._create_right_panel()

    def _create_left_panel(self) -> None:
        """Create the left panel containing the analysis list."""
        self.left_frame = ttk.Frame(self.frame)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.left_frame.rowconfigure(1, weight=1)
        self.left_frame.columnconfigure(0, weight=1)

        # Header with title and refresh button
        self._create_tree_header()

        # Analysis list treeview
        self.tree = ttk.Treeview(self.left_frame, show="tree")
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Vertical scrollbar for analysis list
        self.tree_scrollbar = ttk.Scrollbar(
            self.left_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
        self.tree_scrollbar.grid(row=1, column=1, sticky="ns")

    def _create_tree_header(self) -> None:
        """Create the header frame with title and refresh button."""
        self.tree_header = ttk.Frame(self.left_frame)
        self.tree_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        ttk.Label(
            self.tree_header, text="Output analysis", font=FONTS["heading"]
        ).pack(side="left")

        self.refresh_btn = ttk.Button(
            self.tree_header,
            text="↻ Refresh",
            width=10,
            command=self._on_refresh_click,
        )
        self.refresh_btn.pack(side="right")

    def _create_right_panel(self) -> None:
        """Create the right panel with scrollable content area."""
        right_container = ttk.Frame(self.frame)
        right_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_container.columnconfigure(0, weight=1)
        right_container.rowconfigure(0, weight=1)

        # Create canvas with vertical and horizontal scrollbars
        self.right_canvas = tk.Canvas(right_container, highlightthickness=0, bg="white")
        self.right_scrollbar_v = ttk.Scrollbar(
            right_container, orient="vertical", command=self.right_canvas.yview
        )
        self.right_scrollbar_h = ttk.Scrollbar(
            right_container, orient="horizontal", command=self.right_canvas.xview
        )
        self.right_canvas.configure(
            yscrollcommand=self.right_scrollbar_v.set,
            xscrollcommand=self.right_scrollbar_h.set,
        )

        # Grid layout for canvas and scrollbars
        self.right_canvas.grid(row=0, column=0, sticky="nsew")
        self.right_scrollbar_v.grid(row=0, column=1, sticky="ns")
        self.right_scrollbar_h.grid(row=1, column=0, sticky="ew")

        # Create scrollable frame inside canvas with minimum width
        self.right_panel = ttk.Frame(self.right_canvas)
        self.right_window = self.right_canvas.create_window(
            0, 0, window=self.right_panel, anchor="nw"
        )
        self.right_panel.columnconfigure(0, weight=1, minsize=800)

        # Bind scroll events
        self._setup_scroll_bindings()

        # Create default message and analysis content frames
        self._create_default_message_frame()
        self._create_analysis_content_frame()

    def _setup_scroll_bindings(self) -> None:
        """Configure scroll bindings for the right panel canvas."""

        def on_mousewheel(event):
            """Handle mouse wheel scroll events."""
            self.right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.right_canvas.bind_all("<MouseWheel>", on_mousewheel)

        def on_frame_configure(event):
            """Update scroll region when content frame is resized."""
            self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
            canvas_width = self.right_canvas.winfo_width()
            content_width = self.right_panel.winfo_reqwidth()
            if canvas_width > 1 and canvas_width >= content_width:
                self.right_canvas.itemconfig(self.right_window, width=canvas_width)
            else:
                self.right_canvas.itemconfig(
                    self.right_window, width=max(800, content_width)
                )

        self.right_panel.bind("<Configure>", on_frame_configure)

        def on_canvas_configure(event):
            """Update content frame width when canvas is resized."""
            canvas_width = event.width
            content_width = self.right_panel.winfo_reqwidth()
            if canvas_width > 1:
                if canvas_width >= content_width:
                    self.right_canvas.itemconfig(self.right_window, width=canvas_width)
                else:
                    self.right_canvas.itemconfig(
                        self.right_window, width=max(800, content_width)
                    )

        self.right_canvas.bind("<Configure>", on_canvas_configure)

    def _create_default_message_frame(self) -> None:
        """Create the default message frame shown when no analysis is selected."""
        self.default_message_frame = ttk.Frame(self.right_panel)
        self.default_message_frame.grid(row=0, column=0, sticky="nsew")
        self.default_message_frame.columnconfigure(0, weight=1)
        self.default_message_frame.rowconfigure(0, weight=1)

        default_label = ttk.Label(
            self.default_message_frame,
            text="No analysis selected",
            font=("Segoe UI", 14),
            foreground="gray",
        )
        default_label.grid(row=0, column=0)

    def _create_analysis_content_frame(self) -> None:
        """Create the analysis content frame with summary, metrics, and keywords sections."""
        self.analysis_frame = ttk.Frame(self.right_panel)
        self.analysis_frame.columnconfigure(0, weight=1)

        # Create individual sections
        self._create_summary_section()
        self._create_metrics_section()
        self._create_keywords_section()

    def _create_summary_section(self) -> None:
        """Create the classification summary section with labels and pie chart."""
        self.summary = ttk.LabelFrame(
            self.analysis_frame, text="Classification Summary", padding=10
        )
        self.summary.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # Both columns expandable
        self.summary.columnconfigure(0, weight=1)
        self.summary.columnconfigure(1, weight=1)

        # Left side: Classification count labels
        self.summary_labels_frame = ttk.Frame(self.summary)
        self.summary_labels_frame.grid(row=0, column=0, sticky="w", padx=5, pady=(0, 10))

        self.summary_labels = {}
        for key in ("Producer", "Consumer", "Producer & Consumer"):
            lbl = ttk.Label(
                self.summary_labels_frame, text=f"{key}: 0", font=("Segoe UI", 11)
            )
            lbl.pack(anchor="w", pady=4)
            self.summary_labels[key] = lbl

        # Right side: Pie chart
        self.summary_chart_frame = ttk.Frame(self.summary)
        self.summary_chart_frame.grid(row=0, column=1, sticky="nsew", padx=5)

        self.summary_fig = Figure(figsize=(4, 4), dpi=80)
        self.summary_ax = self.summary_fig.add_subplot(111)
        self.summary_canvas = FigureCanvasTkAgg(self.summary_fig, self.summary_chart_frame)

        widget = self.summary_canvas.get_tk_widget()
        widget.configure(width=320, height=320)
        widget.pack(expand=True, fill="both")

        self.summary_fig.patch.set_facecolor("#ffffff")

    def _create_metrics_section(self) -> None:
        """Create the code metrics section."""
        self.metrics_frame = ttk.LabelFrame(
            self.analysis_frame, text="Code Metrics", padding=10
        )
        self.metrics_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        self.metrics_labels = {}
        for key in ("Media Complexity Cyclomatic", "Media Maintainability Index"):
            lbl = ttk.Label(self.metrics_frame, text=f"{key}: 0", font=("Segoe UI", 11))
            lbl.pack(anchor="w", pady=4)
            self.metrics_labels[key] = lbl

    def _create_keywords_section(self) -> None:
        """Create the ML keywords usage section with table and bar chart."""
        self.libs_frame = ttk.LabelFrame(
            self.analysis_frame, text="ML Keywords Usage", padding=10
        )
        self.libs_frame.grid(row=2, column=0, sticky="nsew")

        self.libs_frame.columnconfigure(0, weight=1)
        self.libs_frame.rowconfigure(0, weight=1)
        self.libs_frame.rowconfigure(1, weight=1)

        # Keywords table
        self._create_keywords_table()

        # Bar chart for keyword occurrences
        self._create_keywords_chart()

    def _create_keywords_table(self) -> None:
        """Create the keywords treeview table."""
        self.libs_tree = ttk.Treeview(
            self.libs_frame,
            columns=("library", "keyword", "occurrences"),
            show="headings",
            height=10,
        )

        # Configure column headings
        self.libs_tree.heading("library", text="Library")
        self.libs_tree.heading("keyword", text="Keyword")
        self.libs_tree.heading("occurrences", text="Occurrences")

        # Configure column widths and alignment
        self.libs_tree.column("library", width=120, anchor="center")
        self.libs_tree.column("keyword", width=150, anchor="center")
        self.libs_tree.column("occurrences", width=80, anchor="center")

        self.libs_tree.grid(row=0, column=0, sticky="nsew")

        # Vertical scrollbar for table
        scrollbar = ttk.Scrollbar(
            self.libs_frame, orient="vertical", command=self.libs_tree.yview
        )
        self.libs_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    #Use the matplotlib library
    def _create_keywords_chart(self) -> None:
        """Create the horizontal bar chart for keywords usage."""
        self.keywords_chart_frame = ttk.Frame(self.libs_frame)
        self.keywords_chart_frame.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0)
        )

        self.keywords_fig = Figure(figsize=(10, 5), dpi=80)
        self.keywords_ax = self.keywords_fig.add_subplot(111)
        self.keywords_canvas = FigureCanvasTkAgg(
            self.keywords_fig, self.keywords_chart_frame
        )
        self.keywords_canvas.get_tk_widget().configure(width=800, height=400)
        self.keywords_canvas.get_tk_widget().pack()
        self.keywords_fig.patch.set_facecolor("#ffffff")

    
    # Event Handlers

    def _on_refresh_click(self) -> None:
        """Handle refresh button click event."""
        self._trigger_callback("on_refresh")

    def _on_tree_select(self, event) -> None:
        """Handle analysis selection in the treeview."""
        selection = self.tree.selection()
        if selection:
            # Show analysis content and trigger callback
            self.show_analysis_content()
            self._trigger_callback("on_analysis_select", selection[0])

    
    # Public Methods - Data Population
    
    def populate_analyses(self, analysis_ids: list) -> None:
        """Populate the analysis list with available analysis IDs.

        Args:
            analysis_ids: List of analysis identifiers to display.
        """
        self.tree.delete(*self.tree.get_children())
        for analysis_id in analysis_ids:
            self.tree.insert("", "end", iid=analysis_id, text=f"Analysis_{analysis_id}")

    def update_summary(self, data: Dict[str, int]) -> None:
        """Update the classification summary labels and pie chart.

        Args:
            data: Dictionary with keys 'Producer', 'Consumer', 'Producer & Consumer'
                  and their respective counts as values.
        """
        # Update label text
        for key, value in data.items():
            if key in self.summary_labels:
                self.summary_labels[key].configure(text=f"{key}: {value}")

        # Update pie chart
        self._update_summary_chart(data)

    def update_metrics(self, data: Dict[str, float]) -> None:
        """Update the code metrics labels.

        Args:
            data: Dictionary with metric names as keys and values as floats.
        """
        for key, value in data.items():
            if key in self.metrics_labels:
                self.metrics_labels[key].configure(text=f"{key}: {value}")

    def update_library(self, data: list) -> None:
        """Update the keywords table and bar chart.

        Args:
            data: List of tuples (library, keyword, occurrences) sorted by
                  occurrences in descending order.
        """
        # Clear existing table rows
        for row in self.libs_tree.get_children():
            self.libs_tree.delete(row)

        # Insert new data
        for library, keyword, occurrences in data:
            self.libs_tree.insert("", "end", values=(library, keyword, occurrences))

        # Update bar chart
        self._update_keywords_chart(data)

    
    # Public Methods - View State Management
    

    def show_default_message(self) -> None:
        """Show the default 'No analysis selected' message and disable scrolling."""
        self.analysis_frame.grid_remove()
        self.default_message_frame.grid(row=0, column=0, sticky="nsew")

        # Disable canvas scrolling when showing default message
        self.right_canvas.unbind_all("<MouseWheel>")
        self.right_canvas.configure(yscrollcommand=None, xscrollcommand=None)
        self.right_scrollbar_v.configure(command=None)
        self.right_scrollbar_h.configure(command=None)

    def show_analysis_content(self) -> None:
        """Show the analysis content and enable scrolling."""
        self.default_message_frame.grid_remove()
        self.analysis_frame.grid(row=0, column=0, sticky="nsew")

        # Re-enable canvas scrolling
        def on_mousewheel(event):
            self.right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.right_canvas.bind_all("<MouseWheel>", on_mousewheel)
        self.right_canvas.configure(
            yscrollcommand=self.right_scrollbar_v.set,
            xscrollcommand=self.right_scrollbar_h.set,
        )
        self.right_scrollbar_v.configure(command=self.right_canvas.yview)
        self.right_scrollbar_h.configure(command=self.right_canvas.xview)

    
    # Private Methods - Chart Updates
    

    def _update_summary_chart(self, data: Dict[str, int]) -> None:
        """Update the pie chart for classification summary.

        Args:
            data: Dictionary with classification counts.
        """
        self.summary_ax.clear()

        # Extract non-zero values for pie chart
        labels = []
        values = []
        colors = ["#4CAF50", "#2196F3", "#FF9800"]

        for key in ("Producer", "Consumer", "Producer & Consumer"):
            val = data.get(key, 0)
            if val > 0:
                labels.append(key.replace(" & ", "\n& "))
                values.append(val)

        # Draw pie chart or show 'No Data' message
        if values and sum(values) > 0:
            self.summary_ax.pie(
                values,
                labels=labels,
                autopct="%1.1f%%",
                colors=colors[: len(values)],
                startangle=90,
            )
            self.summary_ax.set_title("Distribution", fontsize=10, pad=10)
        else:
            self.summary_ax.text(
                0.5,
                0.5,
                "No Data",
                ha="center",
                va="center",
                transform=self.summary_ax.transAxes,
                fontsize=12,
            )

        self.summary_canvas.draw()

    def _update_keywords_chart(self, data: list) -> None:
        """Update the horizontal bar chart for keywords usage.

        Args:
            data: List of tuples (library, keyword, occurrences).
        """
        self.keywords_ax.clear()

        if not data:
            self.keywords_ax.text(
                0.5,
                0.5,
                "No Data",
                ha="center",
                va="center",
                transform=self.keywords_ax.transAxes,
                fontsize=12,
            )
            self.keywords_canvas.draw()
            return

        # Prepare data for horizontal bar chart (top 10)
        labels = [f"{lib}\n{kw}" for lib, kw, _ in data[:10]]
        occurrences = [count for _, _, count in data[:10]]

        # Create horizontal bar chart
        bars = self.keywords_ax.barh(range(len(labels)), occurrences, color="#2196F3")
        self.keywords_ax.set_yticks(range(len(labels)))
        self.keywords_ax.set_yticklabels(labels, fontsize=10)
        self.keywords_ax.set_xlabel("Occurrences", fontsize=11)
        self.keywords_ax.set_title("Top Keywords Usage", fontsize=12, pad=10)
        self.keywords_ax.invert_yaxis()  # Highest value at top

        # Add value labels on bars
        for i, (bar, val) in enumerate(zip(bars, occurrences)):
            self.keywords_ax.text(val, i, f" {val}", va="center", fontsize=10)

        self.keywords_fig.tight_layout()
        self.keywords_canvas.draw()

