"""Main Window - Composes all views into the main application window."""

import tkinter as tk
from typing import Callable

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from gui.views.config_view import ConfigView
from gui.views.output_view import OutputView
from gui.style import PADDING
from gui.views.dashboard_view import DashboardView

class MainWindow:
    """Main application window that composes all views."""

    def __init__(self, root: tk.Tk):
        self.root = root

        

        # Create notebook for tabs
        self.notebook = ttk.Notebook(root, padding=PADDING["small"])
        self.notebook.pack(fill="both", expand=True)

        # Create tab frames
        self.config_tab = ttk.Frame(self.notebook)
        self.output_tab = ttk.Frame(self.notebook)
        self.dashboard_tab = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.config_tab, text="⚙️ Configuration")
        self.notebook.add(self.output_tab, text="📂 Output")
        self.notebook.add(self.dashboard_tab, text="📊 Dashboard")
        
        # Create views
        self.config_view = ConfigView(self.config_tab)
        self.output_view = OutputView(self.output_tab)
        self.dashboard_view = DashboardView(self.dashboard_tab)

        # Show all views in their respective tabs
        self.config_view.show()
        self.output_view.show()

    def get_config_view(self) -> ConfigView:
        """Get the configuration view."""
        return self.config_view

    def get_output_view(self) -> OutputView:
        """Get the output view."""
        return self.output_view

    def switch_to_config_tab(self) -> None:
        """Switch to the configuration tab."""
        self.notebook.select(0)

    def switch_to_output_tab(self) -> None:
        """Switch to the output tab."""
        self.notebook.select(1)

    def show_info(self, title: str, message: str) -> None:
        """Show an information dialog."""
        from tkinter import messagebox

        messagebox.showinfo(title, message)

    def show_error(self, title: str, message: str) -> None:
        """Show an error dialog."""
        from tkinter import messagebox

        messagebox.showerror(title, message)

    def schedule(self, delay_ms: int, callback: Callable) -> str:
        """Schedule a callback to run after a delay."""
        return self.root.after(delay_ms, callback)

    def get_dashboard_view(self):
        return self.dashboard_view
