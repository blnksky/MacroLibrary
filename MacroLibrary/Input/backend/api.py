from __future__ import annotations

from typing import Callable

from .. import keymap
from ..events import InputEvent
from .keyboard import Keyboard
from .mouse import Mouse

__all__ = ["InputAPI", "InputHandler"]


class InputAPI:
    """
    Merged keyboard + mouse facade over a :class:`Backend`.

    This is the low-level API (``Input.press`` / ``Input.mouse.click`` ...).
    High-level binding helpers live in ``Input.base``.
    """

    def __init__(self, backend) -> None:
        self.backend = backend
        self.IIDS = backend.IIDS
        self.keyboard = Keyboard(self)
        self.mouse = Mouse(self)

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------

    def _id(self, identifier: str, device: str | None = None) -> str:
        return keymap.spec(identifier, device=device).id

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def press(self, identifier: str, device: str | None = None) -> None:
        self.backend.press(self._id(identifier, device))

    def release(self, identifier: str, device: str | None = None) -> None:
        self.backend.release(self._id(identifier, device))

    def hold(self, identifier: str, device: str | None = None) -> None:
        self.backend.hold(self._id(identifier, device))

    def is_pressed(self, identifier: str, device: str | None = None) -> bool:
        return self.backend.is_pressed(self._id(identifier, device))

    def release_all(self) -> None:
        self.backend.release_all()

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def send(self, signature, state: bool | None = None) -> bool:
        """Press / release / tap a chord or type literal text."""
        sig = keymap.parse(signature)
        if sig.text is not None:
            self.backend.write(sig.text)
            return True

        state = sig.state if state is None else state
        ids = sig.ids
        if not ids:
            return False

        if state is True:
            for i in ids:
                self.backend.press(i)
        elif state is False:
            for i in reversed(ids):
                self.backend.release(i)
        else:
            for i in reversed(ids):
                self.backend.press(i)
            for i in ids:
                self.backend.release(i)
        return True

    def write(self, text: str, interval: float = 0.0) -> None:
        self.backend.write(text, interval)

    def wait(self, identifier: str, timeout: int | None = None, pressed: bool | None = None) -> bool:
        """Poll-based wait for the low-level API (the binding layer has a better one)."""
        import time

        identifier = self._id(identifier)
        if pressed is None:
            pressed = not self.is_pressed(identifier)

        deadline = None if timeout is None else time.monotonic() + timeout / 1000
        while self.is_pressed(identifier) != pressed:
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(0.001)
        return True

    # ------------------------------------------------------------------
    # Pointer
    # ------------------------------------------------------------------

    def move(self, x: int, y: int, absolute: bool = True) -> None:
        self.backend.move(x, y, absolute)

    def move_to(self, x: int, y: int) -> None:
        self.backend.move_to(x, y)

    def wheel(self, dy: int = 0, dx: int = 0) -> None:
        self.backend.wheel(dy, dx)

    def click(self, button: str = "lbutton", count: int = 1) -> None:
        self.backend.click(self._id(button, "mouse"), count)

    def get_position(self) -> tuple[int, int]:
        return self.backend.get_position()

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def hook(
        self,
        callback: Callable[[InputEvent], object],
        device: str | None = None,
        suppress: bool = False,
    ) -> object:
        if device is None:
            return self.backend.hook(callback, suppress)

        def wrapper(event: InputEvent):
            if event.device != device:
                return False
            return callback(event)

        return self.backend.hook(wrapper, suppress)

    def unhook(self, handle: object) -> None:
        self.backend.unhook(handle)

    def unhook_all(self) -> None:
        self.backend.unhook_all()


InputHandler = InputAPI
