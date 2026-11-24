"""Platform selection + the low level API instance."""

from __future__ import annotations

import sys

from .contract import Backend
from .api import InputAPI, InputHandler

__all__ = [
    "Backend",
    "InputAPI",
    "InputHandler",
    "backend",
    "api",
    "IIDS",
    "keyboard",
    "mouse",
    "press",
    "release",
    "hold",
    "is_pressed",
    "write",
    "send",
    "wait",
    "move",
    "move_to",
    "wheel",
    "click",
    "get_position",
    "hook",
    "unhook",
    "unhook_all",
    "release_all",
]

if sys.platform == "win32":
    from .windows import WindowsBackend as _Backend
elif sys.platform.startswith("linux"):
    from .linux import LinuxBackend as _Backend
else:  # pragma: no cover - explicit failure is better than silent degradation
    raise OSError(f"Unsupported platform: {sys.platform}")

backend: Backend = _Backend()
api = InputAPI(backend)

IIDS = backend.IIDS

keyboard = api.keyboard
mouse = api.mouse

press = api.press
release = api.release
hold = api.hold
is_pressed = api.is_pressed
write = api.write
send = api.send
wait = api.wait

move = api.move
move_to = api.move_to
wheel = api.wheel
click = api.click
get_position = api.get_position

hook = api.hook
unhook = api.unhook
unhook_all = api.unhook_all
release_all = api.release_all
