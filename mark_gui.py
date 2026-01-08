"""Application Entry Point - Initializes and runs the GUI application."""

from pathlib import Path

from gui.style import create_themed_window
from gui.main_window import MainWindow
from gui.controller import AppController
from gui.services.output_reader import OutputReader


APP_TITLE = "MARK 2.0 Plus - ML Automated Rule-Based Classification Kit"
APP_SIZE = (1200, 800)
DEFAULT_IO_PATH = Path("./io")


def main():
    """Main entry point for the GUI application."""
    root = create_themed_window(APP_TITLE, APP_SIZE)

    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (APP_SIZE[0] // 2)
    y = (root.winfo_screenheight() // 2) - (APP_SIZE[1] // 2)
    root.geometry(f"{APP_SIZE[0]}x{APP_SIZE[1]}+{x}+{y}")

    # Initialize services - output is inside io folder
    output_reader = OutputReader(DEFAULT_IO_PATH / "output")

    # Create main window and controller
    main_window = MainWindow(root)
    controller = AppController(main_window=main_window, output_reader=output_reader)

    root.mainloop()


if __name__ == "__main__":
    main()
