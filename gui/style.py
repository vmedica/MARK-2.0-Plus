"""Style configuration for the GUI."""

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *

    HAS_TTKBOOTSTRAP = True
except ImportError:
    import tkinter.ttk as ttk

    HAS_TTKBOOTSTRAP = False

DEFAULT_THEME = "flatly"

FONTS = {
    "default": ("Segoe UI", 10),
    "heading": ("Segoe UI", 12, "bold"),
    "monospace": ("Consolas", 10),
}

PADDING = {"small": 5, "medium": 10, "large": 20}


def apply_style(root) -> None:
    """Apply the application style to the root window."""
    style = ttk.Style()
    if HAS_TTKBOOTSTRAP:
        style.configure("Treeview", font=FONTS["monospace"], rowheight=25)
        style.configure("Treeview.Heading", font=FONTS["heading"])
    else:
        style.theme_use("clam")
        style.configure("Treeview", font=FONTS["monospace"], rowheight=25)
        style.configure("Treeview.Heading", font=FONTS["heading"])


def create_themed_window(title: str, size: tuple = (1200, 800)):
    """Create a themed root window."""
    if HAS_TTKBOOTSTRAP:
        root = ttk.Window(themename=DEFAULT_THEME)
    else:
        import tkinter as tk

        root = tk.Tk()

    root.title(title)
    root.geometry(f"{size[0]}x{size[1]}")
    apply_style(root)
    return root
