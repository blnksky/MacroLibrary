"""
Active-window capture and change notifications, selected for the current
platform.

The Windows implementation imports ``pygetwindow``; that module is never
imported on Linux. The Linux implementation talks to X11 directly through
``python-xlib`` (see ``windows`` and ``linux``).

``changed`` is an :class:`~MacroLibrary.Structures.Event` that receives the new
active-window title whenever it changes. Watching is opt-in: call ``watch()``
to start the polling thread and ``unwatch()`` to stop it. ``Sys.load`` starts
the watcher and uses it to refresh ``Sys.active``.
"""

from __future__ import annotations

from ._platform import getActiveWindowTitle
from .watcher import changed, title, watch, watching, unwatch

__all__ = [
    "getActiveWindowTitle",
    "changed",
    "title",
    "watching",
    "watch",
    "unwatch",
]
