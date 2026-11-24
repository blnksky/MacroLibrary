"""
Session lifecycle: whether the binding layer is active and whether the global
backend hook is installed.

``Session.active`` is the single "suspend" switch (AHK's Suspend). It is
independent of individual ``Bind.enabled`` flags and, crucially, it no longer
gates synthetic ``send()`` calls.
"""

from __future__ import annotations

import threading

from ..Structures import State

__all__ = ["Session"]


class Session:
    def __init__(self, runtime) -> None:
        self.runtime = runtime
        self.active = State(value=True)          # active by default
        self._handle: object | None = None
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Hook lifecycle
    # ------------------------------------------------------------------

    @property
    def installed(self) -> bool:
        return self._handle is not None

    def start(self) -> bool:
        """Install the global hook (idempotent). Returns True when installed now."""
        with self._lock:
            if self._handle is not None:
                return False
            self._handle = self.runtime.backend.hook(
                self.runtime.dispatcher.backend_callback,
                suppress=True,
            )
            return True

    def stop(self) -> bool:
        with self._lock:
            if self._handle is None:
                return False
            self.runtime.backend.unhook(self._handle)
            self._handle = None
            return True

    # ------------------------------------------------------------------
    # Suspension
    # ------------------------------------------------------------------

    def set_active(self, value: bool) -> None:
        self.active.update(bool(value))

    def toggle(self) -> bool:
        self.set_active(not self.active())
        return self.active()

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        self.stop()
        self.runtime.backend.release_all()
        self.runtime.backend.shutdown()
