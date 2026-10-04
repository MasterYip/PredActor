"""BaseGuiPanel — abstract base for per-guidance GUI panels in CustomTkinter.

Each subclass draws its own controls (sliders, checkboxes) and manages
its own ``tk.Variable`` instances.  The :class:`GuiManager` places each
panel in a ``CTkTabview`` tab.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

try:
    import customtkinter as ctk
    import tkinter as tk
    _CTK_AVAILABLE = True
except ImportError:
    _CTK_AVAILABLE = False


class BaseGuiPanel(ABC):
    """Abstract base for a per-guidance-type GUI panel.

    Each subclass:
      - Draws its own controls (sliders, checkboxes) via :meth:`build`
      - Refreshes the shared status bar via :meth:`refresh_status`
      - Reacts to activation changes via :meth:`on_activation_changed`
    """

    guidance_name: str = "Base"

    def __init__(self, guidance):
        """
        Args:
            guidance: The :class:`GuidanceBase` instance this panel controls.
        """
        self.guidance = guidance

    @abstractmethod
    def build(self, parent, root_tk) -> 'ctk.CTkFrame':
        """Build and return the panel widget tree.

        All ``ctk`` widget constructors MUST receive ``master=root_tk`` for
        correct thread-affinity.

        Args:
            parent: The parent ``CTkFrame`` (usually a notebook tab).
            root_tk: The ``CTk`` root, used as ``master=`` for Variable creation.

        Returns:
            The root ``CTkFrame`` of the panel.
        """
        ...

    @abstractmethod
    def refresh_status(self) -> str:
        """Return a status string for the shared status bar."""
        ...

    def on_activation_changed(self, active: bool) -> None:
        """Called when this guidance type is enabled/disabled from the manager.

        Default implementation no-ops; override to grey out widgets.
        """
        pass
