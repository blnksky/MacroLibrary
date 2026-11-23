from threading import RLock

from .keyboard import Keyboard
from .mouse import Mouse
from .keymap import normalize, normalize_mouse


class InputHandler:
    IIDS : set[str]

    def __init__(self, backend):
        self.backend = backend

        self.keyboard = Keyboard(self)
        self.mouse = Mouse(self)

        self.IIDS = backend.IIDS

        self._lock = RLock()
        self._pressed = set()
        self._hooks = {}

    # -------------------------
    # Input identification
    # -------------------------

    def _normalize(self, identifier, device=None):
        if device == "mouse":
            return normalize_mouse(identifier)

        return normalize(identifier)

    def _key(self, identifier, device=None):
        identifier = self._normalize(identifier, device)
        return identifier

    # -------------------------
    # Press / Hold / Release
    # -------------------------

    def press(self, identifier, device=None):
        identifier = self._key(identifier, device)

        with self._lock:
            if identifier in self._pressed:
                return

            self._pressed.add(identifier)

        self.backend.press(identifier)

    def hold(self, identifier, device=None):
        self.press(identifier, device)
        return self

    def release(self, identifier, device=None):
        identifier = self._key(identifier, device)

        with self._lock:
            if identifier not in self._pressed:
                return

            self._pressed.discard(identifier)

        self.backend.release(identifier)

    def is_pressed(self, identifier):
        identifier = self._key(identifier)
        return identifier in self._pressed

    def write(self, text: str, interval: float = 0):
        return self.backend.write(text, interval=interval)

    # -------------------------
    # Hooks
    # -------------------------

    def hook(self, callback, device=None, suppress=False):
        def wrapped(event):
            if device is None or event.device == device:
                return callback(event)
            return False

        handle = self.backend.hook(wrapped, suppress=suppress)
        self._hooks[handle] = wrapped
        return handle

    def unhook(self, handle):
        if handle not in self._hooks:
            return

        self.backend.unhook(handle)
        del self._hooks[handle]

    def unhook_all(self):
        for handle in list(self._hooks):
            self.unhook(handle)

    # -------------------------
    # Unified event handling
    # -------------------------

    def release_all(self):
        with self._lock:
            keys = list(self._pressed)

        for key in keys:
            self.release(key)
