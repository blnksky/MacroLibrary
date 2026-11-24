"""
Physical input state.

This replaces the globals (``inputStates``, ``inputQueue``, ``stateTS``) and the
import-time cleanup thread of the old ``base.py``. State is always tracked,
even while the binding system is suspended, so ``get()`` / ``is_pressed()``
stay truthful before a hook is installed and during suspension.
"""

from __future__ import annotations

import threading

from . import keymap
from .events import InputEvent
from ..common import now

__all__ = ["InputState"]


class InputState:
    def __init__(self, buffer: int = 100) -> None:
        self.buffer = buffer
        self._counts: dict[str, int] = {}
        self._queue: list[str] = []
        self._timestamps: dict[str, int] = {}
        self._condition = threading.Condition(threading.RLock())

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    def track(self, event: InputEvent) -> None:
        """Record a physical or injected event."""
        if event.event_type not in ("down", "up"):
            return

        with self._condition:
            if event.event_type == "down":
                self._counts[event.id] = 1
                if event.id in self._queue:
                    self._queue.remove(event.id)
                self._queue.insert(0, event.id)
                self._timestamps[event.id + " down"] = now()
            else:
                if event.id in self._counts:
                    self._counts[event.id] = 0
                self._timestamps[event.id + " up"] = now()
            self._condition.notify_all()

    def reset(self) -> None:
        with self._condition:
            self._counts.clear()
            self._queue.clear()
            self._timestamps.clear()
            self._condition.notify_all()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def pressed(self, identifier: str) -> bool:
        """True when ``identifier`` (generic modifiers included) is down."""
        try:
            s = keymap.spec(identifier)
        except keymap.UnknownInput:
            return False
        with self._condition:
            return any(self._counts.get(part, 0) > 0 for part in (s.id, *s.sides))

    def get(self, input) -> bool:
        """True when every id in a signature is currently down."""
        try:
            sig = keymap.parse(input)
        except (keymap.UnknownInput, ValueError):
            return False
        if not sig.ids:
            return False
        return all(self.pressed(i) for i in sig.ids)

    def queue(self) -> tuple[str, ...]:
        with self._condition:
            return tuple(self._queue)

    def last(self, identifier: str, state: bool | None = None):
        """Return the last state-change timestamp (or ``(state, timestamp)``)."""
        i = keymap.normalize(identifier)
        if state is not None:
            return self._timestamps.get(i + (" down" if state else " up"), 0)
        down = self.last(i, True)
        up = self.last(i, False)
        return (down >= up, down if down >= up else up)

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def wait(self, identifier: str, timeout: int | None = None, pressed: bool | None = None):
        """
        Block until ``identifier`` reaches ``pressed``.

        With no explicit ``pressed`` value the *opposite* of the current state
        is awaited, matching the historical ``Input.wait`` behaviour: calling
        ``wait(id)`` inside a down callback waits for the matching release.
        Returns ``True``/``False`` for "reached / timed out"; without a timeout
        it returns the final logical state.
        """
        try:
            sig = keymap.parse(identifier)
        except (keymap.UnknownInput, ValueError):
            return False

        if pressed is None:
            pressed = sig.state if sig.state is not None else not self.get(sig.ids[0] if sig.ids else identifier)

        def reached() -> bool:
            return all(self.pressed(i) for i in sig.ids) == pressed if sig.ids else True

        with self._condition:
            if reached():
                return True
            if not self._condition.wait_for(reached, None if timeout is None else timeout / 1000):
                return False
            return True
