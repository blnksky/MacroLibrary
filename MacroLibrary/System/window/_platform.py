"""
Platform selection for active-window capture.

Kept separate from ``__init__`` so the watcher can import the capture function
without creating an import cycle through the package initialiser.
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from .windows import getActiveWindowTitle
elif sys.platform.startswith("linux"):
    from .linux import getActiveWindowTitle
else:
    def getActiveWindowTitle() -> str | None:
        """No active-window backend is implemented for this platform."""
        return None


__all__ = ["getActiveWindowTitle"]
