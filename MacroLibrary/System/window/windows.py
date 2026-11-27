"""Active-window title on Windows (via ``pygetwindow``)."""

from __future__ import annotations

import pygetwindow

__all__ = ["getActiveWindowTitle"]


def getActiveWindowTitle() -> str | None:
    """Return the title of the foreground window, or ``None``."""
    try:
        window = pygetwindow.getActiveWindow()
    except Exception:
        return None

    if window is None:
        return None

    title = getattr(window, "title", None)
    return None if title is None else str(title)
