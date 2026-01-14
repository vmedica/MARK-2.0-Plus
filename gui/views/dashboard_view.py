# C:\ISTA_Progetti\MARK-2.0-Plus\gui\views\dashboard_view.py
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from typing import Callable, Dict
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class DashboardView:
    def __init__(self, parent):
        self.parent = parent
        self.callbacks: Dict[str, Callable] = {}

        self.container = ttk.Frame(parent)
        self.container.pack(fill="both", expand=True)

        self.container.columnconfigure(0, weight=1)
        self.container.columnconfigure(1, weight=3)
        self.container.rowconfigure(0, weight=1)

        # LEFT – analysis list with scrollbar
        self.left_frame = ttk.Frame(self.container)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.left_frame.rowconfigure(1, weight=1)
        self.left_frame.columnconfigure(0, weight=1)

        # Header with title and refresh button
        self.tree_header = ttk.Frame(self.left_frame)
        self.tree_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
        ttk.Label(self.tree_header, text="Output analysis", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.refresh_btn = ttk.Button(self.tree_header, text="↻ Refresh", width=10)
        self.refresh_btn.pack(side="right")

        self.tree = ttk.Treeview(self.left_frame, show="tree")
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Scrollbar for analysis list
        self.tree_scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
        self.tree_scrollbar.grid(row=1, column=1, sticky="ns")

        # RIGHT – main panel with scrollbar
        
        
        right_container = ttk.Frame(self.container)
        right_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_container.columnconfigure(0, weight=1)
        right_container.rowconfigure(0, weight=1)
        
        # Create canvas and scrollbars (vertical and horizontal)
        self.right_canvas = tk.Canvas(right_container, highlightthickness=0, bg='white')
        self.right_scrollbar_v = ttk.Scrollbar(right_container, orient="vertical", command=self.right_canvas.yview)
        self.right_scrollbar_h = ttk.Scrollbar(right_container, orient="horizontal", command=self.right_canvas.xview)
        self.right_canvas.configure(yscrollcommand=self.right_scrollbar_v.set, xscrollcommand=self.right_scrollbar_h.set)
        
        self.right_canvas.grid(row=0, column=0, sticky="nsew")
        self.right_scrollbar_v.grid(row=0, column=1, sticky="ns")
        self.right_scrollbar_h.grid(row=1, column=0, sticky="ew")
        
        # Create frame inside canvas with minimum width
        self.right_panel = ttk.Frame(self.right_canvas)
        self.right_window = self.right_canvas.create_window(0, 0, window=self.right_panel, anchor="nw")
        self.right_panel.columnconfigure(0, weight=1, minsize=800)  # Set minimum width
        
        # Bind canvas scroll
        def _on_mousewheel(event):
            self.right_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.right_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Update scroll region
        def _on_frame_configure(event):
            self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
            # Only update width if canvas is wider than minimum content width
            canvas_width = self.right_canvas.winfo_width()
            content_width = self.right_panel.winfo_reqwidth()
            if canvas_width > 1 and canvas_width >= content_width:
                self.right_canvas.itemconfig(self.right_window, width=canvas_width)
            else:
                self.right_canvas.itemconfig(self.right_window, width=max(800, content_width))
        
        self.right_panel.bind("<Configure>", _on_frame_configure)
        
        # Update canvas window width when canvas is resized
        def _on_canvas_configure(event):
            canvas_width = event.width
            content_width = self.right_panel.winfo_reqwidth()
            if canvas_width > 1:
                if canvas_width >= content_width:
                    self.right_canvas.itemconfig(self.right_window, width=canvas_width)
                else:
                    self.right_canvas.itemconfig(self.right_window, width=max(800, content_width))
        
        self.right_canvas.bind("<Configure>", _on_canvas_configure)
        
        # --- Default message frame (shown when no analysis is selected) ---
        self.default_message_frame = ttk.Frame(self.right_panel)
        self.default_message_frame.grid(row=0, column=0, sticky="nsew")
        self.default_message_frame.columnconfigure(0, weight=1)
        self.default_message_frame.rowconfigure(0, weight=1)
        
        default_label = ttk.Label(
            self.default_message_frame,
            text="No analysis selected",
            font=("Segoe UI", 14),
            foreground="gray"
        )
        default_label.grid(row=0, column=0)
        
        # --- Analysis content frame (hidden by default) ---
        self.analysis_frame = ttk.Frame(self.right_panel)
        self.analysis_frame.columnconfigure(0, weight=1)
        
        # --- Summary ---
        self.summary = ttk.LabelFrame(self.analysis_frame, text="Classification Summary", padding=10)
        self.summary.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # entrambe le colonne espandibili
        self.summary.columnconfigure(0, weight=1)
        self.summary.columnconfigure(1, weight=1)

        # Labels on top
        self.summary_labels_frame = ttk.Frame(self.summary)
        self.summary_labels_frame.grid(row=0, column=0, sticky="w", padx=5, pady=(0, 10))

        self.summary_labels = {}
        for key in ("Producer", "Consumer", "Producer & Consumer"):
            lbl = ttk.Label(self.summary_labels_frame, text=f"{key}: 0", font=("Segoe UI", 11))
            lbl.pack(anchor="w", pady=4)
            self.summary_labels[key] = lbl

        # Pie Chart
        self.summary_chart_frame = ttk.Frame(self.summary)
        self.summary_chart_frame.grid(row=0, column=1, sticky="nsew", padx=5)

        self.summary_fig = Figure(figsize=(4, 4), dpi=80)
        self.summary_ax = self.summary_fig.add_subplot(111)
        self.summary_canvas = FigureCanvasTkAgg(self.summary_fig, self.summary_chart_frame)

        widget = self.summary_canvas.get_tk_widget()
        widget.configure(width=320, height=320)
        widget.pack(expand=True, fill="both")

        self.summary_fig.patch.set_facecolor("#ffffff")


        # --- Metrics ---
        self.metrics_frame = ttk.LabelFrame(self.analysis_frame, text="Code Metrics", padding=10)
        self.metrics_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        self.metrics_labels = {}
        for key in ("Media Complexity Cyclomatic", "Media Maintainability Index"):
            lbl = ttk.Label(self.metrics_frame, text=f"{key}: 0", font=("Segoe UI", 11))
            lbl.pack(anchor="w", pady=4)
            self.metrics_labels[key] = lbl

        # --- Keywords ---
        self.libs_frame = ttk.LabelFrame(self.analysis_frame, text="ML Keywords Usage", padding=10)
        self.libs_frame.grid(row=2, column=0, sticky="nsew")
        
        self.libs_frame.columnconfigure(0, weight=1)
        self.libs_frame.rowconfigure(0, weight=1)
        self.libs_frame.rowconfigure(1, weight=1)
        
        # Table
        self.libs_tree = ttk.Treeview(
            self.libs_frame, 
            columns=("library", "keyword", "occurrences"), 
            show="headings",
            height=10)
        
        self.libs_tree.heading("library", text="Library")
        self.libs_tree.heading("keyword", text="Keyword")
        self.libs_tree.heading("occurrences", text="Occurrences")
        
        self.libs_tree.column("library", width=120, anchor="center")
        self.libs_tree.column("keyword", width=150, anchor="center")
        self.libs_tree.column("occurrences", width=80, anchor="center")

        self.libs_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.libs_frame, orient="vertical", command=self.libs_tree.yview)
        self.libs_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bar Chart
        self.keywords_chart_frame = ttk.Frame(self.libs_frame)
        self.keywords_chart_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        self.keywords_fig = Figure(figsize=(10, 5), dpi=80)
        self.keywords_ax = self.keywords_fig.add_subplot(111)
        self.keywords_canvas = FigureCanvasTkAgg(self.keywords_fig, self.keywords_chart_frame)
        self.keywords_canvas.get_tk_widget().configure(width=800, height=400)  # Fixed size
        self.keywords_canvas.get_tk_widget().pack()
        self.keywords_fig.patch.set_facecolor("#ffffff")

    # --- Callbacks --- 
    def register_callback(self, name: str, fn: Callable):
        self.callbacks[name] = fn
        # Bind refresh button when callback is registered
        if name == "on_refresh":
            self.refresh_btn.configure(command=self._on_refresh_click)

    def _on_refresh_click(self):
        """Handle refresh button click."""
        if "on_refresh" in self.callbacks:
            self.callbacks["on_refresh"]()

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
        
        # Update pie chart
        self._update_summary_chart(data)

    # --- Aggiorna Metrics ---
    def update_metrics(self, data: Dict[str, float]):
        for key, value in data.items():
            if key in self.metrics_labels:  # evita KeyError
                self.metrics_labels[key].configure(text=f"{key}: {value}")

    # --- Evento selezione analisi ---
    def _on_select(self, _):
        sel = self.tree.selection()
        if sel and "on_analysis_select" in self.callbacks:
            # Show analysis frame and hide default message
            self.show_analysis_content()
            self.callbacks["on_analysis_select"](sel[0])

    # --- Show/Hide Content ---
    def show_default_message(self):
        """Show default 'No analysis selected' message and hide analysis content."""
        self.analysis_frame.grid_remove()
        self.default_message_frame.grid(row=0, column=0, sticky="nsew")
    
    def show_analysis_content(self):
        """Show analysis content and hide default message."""
        self.default_message_frame.grid_remove()
        self.analysis_frame.grid(row=0, column=0, sticky="nsew")
    
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
        
        # Update bar chart
        self._update_keywords_chart(data)
    
    def _update_summary_chart(self, data: Dict[str, int]):
        """Update the    for classification summary."""
        self.summary_ax.clear()
        
        # Extract values, excluding "Producer & Consumer" from pie
        labels = []
        values = []
        colors = ['#4CAF50', '#2196F3', '#FF9800']
        
        for key in ("Producer", "Consumer", "Producer & Consumer"):
            val = data.get(key, 0)
            if val > 0:
                labels.append(key.replace(" & ", "\n& "))
                values.append(val)
        
        if values and sum(values) > 0:
            self.summary_ax.pie(values, labels=labels, autopct='%1.1f%%', 
                               colors=colors[:len(values)], startangle=90)
            self.summary_ax.set_title("Distribution", fontsize=10, pad=10)
        else:
            self.summary_ax.text(0.5, 0.5, 'No Data', ha='center', va='center', 
                                transform=self.summary_ax.transAxes, fontsize=12)
        
        self.summary_canvas.draw()
    
    def _update_keywords_chart(self, data: list):
        """Update the bar chart for keywords usage."""
        self.keywords_ax.clear()
        
        if not data:
            self.keywords_ax.text(0.5, 0.5, 'No Data', ha='center', va='center',
                                 transform=self.keywords_ax.transAxes, fontsize=12)
            self.keywords_canvas.draw()
            return
        
        # Prepare data for horizontal bar chart
        labels = [f"{lib}\n{kw}" for lib, kw, _ in data[:10]]
        occurrences = [count for _, _, count in data[:10]]
        
        # Create horizontal bar chart
        bars = self.keywords_ax.barh(range(len(labels)), occurrences, color='#2196F3')
        self.keywords_ax.set_yticks(range(len(labels)))
        self.keywords_ax.set_yticklabels(labels, fontsize=10)
        self.keywords_ax.set_xlabel('Occurrences', fontsize=11)
        self.keywords_ax.set_title('Top Keywords Usage', fontsize=12, pad=10)
        self.keywords_ax.invert_yaxis()  # Highest at top
        
        # Add value labels on bars
        for i, (bar, val) in enumerate(zip(bars, occurrences)):
            self.keywords_ax.text(val, i, f' {val}', va='center', fontsize=10)
        
        self.keywords_fig.tight_layout()
        self.keywords_canvas.draw()

