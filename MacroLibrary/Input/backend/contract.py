"""
The backend contract.

Both operating systems implement this class. Shared behaviour (held-state,
hook registry, generic modifiers, argument validation) lives here; each backend
only implements the raw OS operations.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Callable

from .. import keymap
from ..events import InputEvent

__all__ = ["Backend"]


class Backend(ABC):
    IIDS = keymap.IIDS

    def __init__(self) -> None:
        self._held: set[str] = set()
        self._lock = threading.RLock()
        self._hooks: dict[object, tuple[Callable[[InputEvent], object], bool]] = {}
        self._hooks_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Synthetic state
    # ------------------------------------------------------------------

    def press(self, identifier: str) -> None:
        s = keymap.spec(identifier)

        if s.kind == "wheel":
            self._wheel(s.axis, s.direction)
            return

        key = s.sides[0] if s.sides else s.id
        with self._lock:
            if key in self._held:
                return
            self._held.add(key)
        try:
            self._press(s)
        except BaseException:
            with self._lock:
                self._held.discard(key)
            raise

    def release(self, identifier: str) -> None:
        s = keymap.spec(identifier)

        if s.kind == "wheel":
            return

        key = s.sides[0] if s.sides else s.id
        with self._lock:
            if key not in self._held:
                return
            self._held.discard(key)
        self._release(s)

    def hold(self, identifier: str) -> None:
        self.press(identifier)

    def is_pressed(self, identifier: str) -> bool:
        s = keymap.spec(identifier)
        if s.kind == "wheel":
            return False

        parts = (s.id, *s.sides)
        with self._lock:
            if any(part in self._held for part in parts):
                return True
        return any(self._is_physically_pressed(keymap.spec(part)) for part in parts)

    def release_all(self) -> None:
        with self._lock:
            held = tuple(self._held)
        for identifier in held:
            try:
                self.release(identifier)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def hook(self, callback: Callable[[InputEvent], object], suppress: bool = False) -> object:
        if not callable(callback):
            raise TypeError("callback must be callable")

        self.start()

        handle = object()
        with self._hooks_lock:
            self._hooks[handle] = (callback, bool(suppress))
        self._on_hooks_changed()
        return handle

    def unhook(self, handle: object) -> None:
        with self._hooks_lock:
            self._hooks.pop(handle, None)
            empty = not self._hooks
        if empty:
            self._on_idle()

    def unhook_all(self) -> None:
        with self._hooks_lock:
            self._hooks.clear()
        self._on_idle()

    def _dispatch(self, event: InputEvent) -> bool:
        with self._hooks_lock:
            hooks = tuple(self._hooks.values())

        suppress = False
        for callback, blocking in hooks:
            try:
                result = callback(event)
            except Exception:
                import traceback

                traceback.print_exc()
                continue
            if blocking and result is True:
                suppress = True
        return suppress

    # ------------------------------------------------------------------
    # Pointer / text convenience
    # ------------------------------------------------------------------

    def move(self, x: int, y: int, absolute: bool = True) -> None:
        self._move(int(x), int(y), bool(absolute))

    def move_to(self, x: int, y: int) -> None:
        self.move(x, y, absolute=True)

    def wheel(self, dy: int = 0, dx: int = 0) -> None:
        if dy:
            self._wheel("y", 1 if dy > 0 else -1)
        if dx:
            self._wheel("x", 1 if dx > 0 else -1)

    def click(self, button: str = "lbutton", count: int = 1) -> None:
        for _ in range(max(1, int(count))):
            self.press(button)
            self.release(button)

    def get_position(self) -> tuple[int, int]:
        return self._get_position()

    def write(self, text: str, interval: float = 0.0) -> None:
        if text:
            self._write(str(text), float(interval))

    def __enter__(self) -> "Backend":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.shutdown()

    # ------------------------------------------------------------------
    # Platform implementation
    # ------------------------------------------------------------------

    @abstractmethod
    def start(self) -> None: ...

    def shutdown(self) -> None:
        self.unhook_all()
        self.release_all()

    @abstractmethod
    def _press(self, spec: keymap.KeySpec) -> None: ...

    @abstractmethod
    def _release(self, spec: keymap.KeySpec) -> None: ...

    @abstractmethod
    def _write(self, text: str, interval: float) -> None: ...

    @abstractmethod
    def _move(self, x: int, y: int, absolute: bool) -> None: ...

    @abstractmethod
    def _get_position(self) -> tuple[int, int]: ...

    @abstractmethod
    def _wheel(self, axis: str, direction: int) -> None: ...

    def _is_physically_pressed(self, spec: keymap.KeySpec) -> bool:
        return False

    def _on_hooks_changed(self) -> None:
        """Called after a hook is added (Linux grabs devices here)."""

    def _on_idle(self) -> None:
        """Called when the last hook is removed."""
