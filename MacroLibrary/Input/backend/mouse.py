from __future__ import annotations

__all__ = ["Mouse"]


class Mouse:
    """Standard ``mouse``-style view over the merged API."""

    def __init__(self, api) -> None:
        self.api = api

    def press(self, button: str = "lbutton") -> None:
        self.api.press(button, device="mouse")

    def release(self, button: str = "lbutton") -> None:
        self.api.release(button, device="mouse")

    def hold(self, button: str = "lbutton") -> None:
        self.api.hold(button, device="mouse")

    def is_pressed(self, button: str = "lbutton") -> bool:
        return self.api.is_pressed(button, device="mouse")

    def click(self, button: str = "lbutton", count: int = 1) -> None:
        self.api.click(button, count)

    def move(self, x: int, y: int, absolute: bool = True) -> None:
        self.api.move(x, y, absolute)

    def move_to(self, x: int, y: int) -> None:
        self.api.move_to(x, y)

    def wheel(self, dy: int = 0, dx: int = 0) -> None:
        self.api.wheel(dy, dx)

    def get_position(self) -> tuple[int, int]:
        return self.api.get_position()

    def hook(self, callback, suppress: bool = False):
        return self.api.hook(callback, device="mouse", suppress=suppress)

    def unhook(self, handle) -> None:
        self.api.unhook(handle)
