"""Base View - Abstract base class for all views."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict


class BaseView(ABC):
    """Abstract base class for all views."""

    def __init__(self, parent):
        self.parent = parent
        self.frame = None
        self._callbacks: Dict[str, Callable] = {}

    @abstractmethod
    def create_widgets(self) -> None:
        """Create and layout all widgets for this view."""
        pass

    def register_callback(self, event_name: str, callback: Callable) -> None:
        """Register a callback for a specific event."""
        self._callbacks[event_name] = callback

    def _trigger_callback(self, event_name: str, *args, **kwargs) -> Any:
        """Trigger a registered callback."""
        callback = self._callbacks.get(event_name)
        if callback:
            return callback(*args, **kwargs)
        return None

    def show(self) -> None:
        """Make this view visible."""
        if self.frame:
            self.frame.pack(fill="both", expand=True)

    def hide(self) -> None:
        """Hide this view."""
        if self.frame:
            self.frame.pack_forget()
