
import sys

if sys.platform == "win32":
    from . import input_windows as backend
elif sys.platform.startswith("linux"):
    from . import input_linux as backend
else:
    raise OSError(f"Unsupported platform: {sys.platform}")

from .handler import InputHandler
from .events import InputEvent

_handler = InputHandler(backend)

# Unified namespaces
keyboard = _handler.keyboard
mouse = _handler.mouse

# Unified constants
IIDS = _handler.IIDS

# Unified shortcuts
hook = _handler.hook
unhook = _handler.unhook

press = _handler.press
hold = _handler.hold
release = _handler.release

is_pressed = _handler.is_pressed

write = _handler.write


__all__ = [
    "IIDS",

    "keyboard",
    "mouse",
    "hook",
    "unhook",
    "press",
    "hold",
    "release",
    "is_pressed",

    "InputEvent",
    "InputHandler",
]
