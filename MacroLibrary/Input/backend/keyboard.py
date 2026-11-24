from __future__ import annotations

__all__ = ["Keyboard"]


class Keyboard:
    """Standard ``keyboard``-style view over the merged API."""

    def __init__(self, api) -> None:
        self.api = api

    def press(self, key: str) -> None:
        self.api.press(key, device="keyboard")

    def release(self, key: str) -> None:
        self.api.release(key, device="keyboard")

    def hold(self, key: str) -> None:
        self.api.hold(key, device="keyboard")

    def is_pressed(self, key: str) -> bool:
        return self.api.is_pressed(key, device="keyboard")

    def send(self, signature, state: bool | None = None) -> bool:
        return self.api.send(signature, state)

    def write(self, text: str, interval: float = 0.0) -> None:
        self.api.write(text, interval)

    def wait(self, key: str, timeout: int | None = None, pressed: bool | None = None) -> bool:
        return self.api.wait(key, timeout, pressed)

    def hook(self, callback, suppress: bool = False):
        return self.api.hook(callback, device="keyboard", suppress=suppress)

    def unhook(self, handle) -> None:
        self.api.unhook(handle)
