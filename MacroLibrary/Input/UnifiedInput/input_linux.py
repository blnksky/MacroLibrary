
from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable

from evdev import InputDevice, UInput, ecodes, list_devices


@dataclass
class InputEvent:
    id: str
    device: str
    event_type: str
    scan_code: int | None = None
    vk_code: int | None = None
    x: int | None = None
    y: int | None = None
    delta: int | None = None
    injected: bool = False
    device_id: str | None = None


# Linux evdev key codes -> AHK-style names.
KEY_NAMES = {
    "KEY_ESC": "esc",
    "KEY_ENTER": "enter",
    "KEY_KPENTER": "numpadenter",
    "KEY_SPACE": "space",
    "KEY_TAB": "tab",
    "KEY_BACKSPACE": "backspace",
    "KEY_DELETE": "delete",
    "KEY_INSERT": "insert",
    "KEY_HOME": "home",
    "KEY_END": "end",
    "KEY_PAGEUP": "pgup",
    "KEY_PAGEDOWN": "pgdn",
    "KEY_UP": "up",
    "KEY_DOWN": "down",
    "KEY_LEFT": "left",
    "KEY_RIGHT": "right",
    "KEY_LEFTSHIFT": "lshift",
    "KEY_RIGHTSHIFT": "rshift",
    "KEY_LEFTCTRL": "lctrl",
    "KEY_RIGHTCTRL": "rctrl",
    "KEY_LEFTALT": "lalt",
    "KEY_RIGHTALT": "ralt",
    "KEY_LEFTMETA": "lwin",
    "KEY_RIGHTMETA": "rwin",
    "KEY_CAPSLOCK": "capslock",
    "KEY_NUMLOCK": "numlock",
    "KEY_SCROLLLOCK": "scrolllock",
    "KEY_COMPOSE": "appskey",
    "BTN_LEFT": "lbutton",
    "BTN_RIGHT": "rbutton",
    "BTN_MIDDLE": "mbutton",
    "BTN_SIDE": "xbutton1",
    "BTN_EXTRA": "xbutton2",
}

for i in range(1, 13):
    KEY_NAMES[f"KEY_F{i}"] = f"f{i}"

for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEY_NAMES[f"KEY_{letter}"] = letter.lower()

for digit in "0123456789":
    KEY_NAMES[f"KEY_{digit}"] = digit

for name in (
    "minus", "equal", "leftbrace", "rightbrace", "backslash",
    "semicolon", "apostrophe", "grave", "comma", "dot", "slash",
):
    KEY_NAMES[f"KEY_{name.upper()}"] = name

IIDS = set(KEY_NAMES.values())

NAME_TO_CODE = {
    name: getattr(ecodes, code_name)
    for code_name, name in KEY_NAMES.items()
    if hasattr(ecodes, code_name)
}

CHAR_MAP = {
    "a": ("KEY_A", False),
    "b": ("KEY_B", False),
    "c": ("KEY_C", False),
    "d": ("KEY_D", False),
    "e": ("KEY_E", False),
    "f": ("KEY_F", False),
    "g": ("KEY_G", False),
    "h": ("KEY_H", False),
    "i": ("KEY_I", False),
    "j": ("KEY_J", False),
    "k": ("KEY_K", False),
    "l": ("KEY_L", False),
    "m": ("KEY_M", False),
    "n": ("KEY_N", False),
    "o": ("KEY_O", False),
    "p": ("KEY_P", False),
    "q": ("KEY_Q", False),
    "r": ("KEY_R", False),
    "s": ("KEY_S", False),
    "t": ("KEY_T", False),
    "u": ("KEY_U", False),
    "v": ("KEY_V", False),
    "w": ("KEY_W", False),
    "x": ("KEY_X", False),
    "y": ("KEY_Y", False),
    "z": ("KEY_Z", False),

    "A": ("KEY_A", True),
    "B": ("KEY_B", True),
    "C": ("KEY_C", True),
    "D": ("KEY_D", True),
    "E": ("KEY_E", True),
    "F": ("KEY_F", True),
    "G": ("KEY_G", True),
    "H": ("KEY_H", True),
    "I": ("KEY_I", True),
    "J": ("KEY_J", True),
    "K": ("KEY_K", True),
    "L": ("KEY_L", True),
    "M": ("KEY_M", True),
    "N": ("KEY_N", True),
    "O": ("KEY_O", True),
    "P": ("KEY_P", True),
    "Q": ("KEY_Q", True),
    "R": ("KEY_R", True),
    "S": ("KEY_S", True),
    "T": ("KEY_T", True),
    "U": ("KEY_U", True),
    "V": ("KEY_V", True),
    "W": ("KEY_W", True),
    "X": ("KEY_X", True),
    "Y": ("KEY_Y", True),
    "Z": ("KEY_Z", True),

    " ": ("KEY_SPACE", False),
    "\n": ("KEY_ENTER", False),
    "\t": ("KEY_TAB", False),

    "1": ("KEY_1", False),
    "2": ("KEY_2", False),
    "3": ("KEY_3", False),
    "4": ("KEY_4", False),
    "5": ("KEY_5", False),
    "6": ("KEY_6", False),
    "7": ("KEY_7", False),
    "8": ("KEY_8", False),
    "9": ("KEY_9", False),
    "0": ("KEY_0", False),

    "!": ("KEY_1", True),
    "@": ("KEY_2", True),
    "#": ("KEY_3", True),
    "$": ("KEY_4", True),
    "%": ("KEY_5", True),
    "^": ("KEY_6", True),
    "&": ("KEY_7", True),
    "*": ("KEY_8", True),
    "(": ("KEY_9", True),
    ")": ("KEY_0", True),

    "-": ("KEY_MINUS", False),
    "_": ("KEY_MINUS", True),
    "=": ("KEY_EQUAL", False),
    "+": ("KEY_EQUAL", True),
    "[": ("KEY_LEFTBRACE", False),
    "{": ("KEY_LEFTBRACE", True),
    "]": ("KEY_RIGHTBRACE", False),
    "}": ("KEY_RIGHTBRACE", True),
    ";": ("KEY_SEMICOLON", False),
    ":": ("KEY_SEMICOLON", True),
    "'": ("KEY_APOSTROPHE", False),
    '"': ("KEY_APOSTROPHE", True),
    "`": ("KEY_GRAVE", False),
    "~": ("KEY_GRAVE", True),
    "\\": ("KEY_BACKSLASH", False),
    "|": ("KEY_BACKSLASH", True),
    ",": ("KEY_COMMA", False),
    "<": ("KEY_COMMA", True),
    ".": ("KEY_DOT", False),
    ">": ("KEY_DOT", True),
    "/": ("KEY_SLASH", False),
    "?": ("KEY_SLASH", True),
}

# Additional convenient aliases.
ALIASES = {
    "return": "enter",
    "esc": "esc",
    "control": "lctrl",
    "ctrl": "lctrl",
    "shift": "lshift",
    "alt": "lalt",
    "win": "lwin",
    "pgdown": "pgdn",
    "pageup": "pgup",
    "pagedown": "pgdn",
    "leftbutton": "lbutton",
    "rightbutton": "rbutton",
    "middlebutton": "mbutton",
}

NAME_TO_CODE.update({
    "wheelup": None,
    "wheeldown": None,
})


def _normalise(name: str) -> str:
    name = str(name).lower().strip()
    return ALIASES.get(name, name)


class Backend:
    """
    Linux input backend using evdev + uinput.

    hook(callback, suppress=False)
    unhook(handle)
    press(key)
    hold(key)
    release(key)
    is_pressed(key)
    release_all()
    shutdown()

    With suppress=True, physical devices are grabbed and events are
    re-emitted through a virtual device unless a callback returns True.
    """

    def __init__(self, grab_devices: bool = True):
        self.grab_devices = grab_devices

        self._lock = threading.RLock()
        self._stop = threading.Event()

        self._devices: dict[str, InputDevice] = {}
        self._threads: list[threading.Thread] = []
        self._hooks: dict[int, tuple[Callable, bool]] = {}
        self._next_hook_id = 1

        self._uinput: UInput | None = None
        self._injected_pressed: set[str] = set()
        self._physical_pressed: set[str] = set()

        self._started = False
        self._suppress_enabled = False

    # ---------------------------------------------------------
    # Device setup
    # ---------------------------------------------------------

    def start(self):
        with self._lock:
            if self._started:
                return

            paths = list_devices()
            capabilities = {}

            for path in paths:
                try:
                    dev = InputDevice(path)
                    caps = dev.capabilities()
                    if not self._is_input_device(caps):
                        dev.close()
                        continue

                    self._devices[path] = dev

                    for event_type, codes in caps.items():
                        if event_type in (
                            ecodes.EV_SYN,
                            ecodes.EV_FF,
                            ecodes.EV_PWR,
                        ):
                            continue

                        existing = set(capabilities.get(event_type, []))
                        existing.update(
                            code for code in codes
                            if isinstance(code, int)
                        )
                        capabilities[event_type] = sorted(existing)

                except (OSError, PermissionError):
                    continue

            if not self._devices:
                raise RuntimeError(
                    "No readable input devices found. Check /dev/input permissions."
                )

            try:
                self._uinput = UInput(
                    events=capabilities,
                    name="Unified Input Virtual Device",
                    vendor=0x1234,
                    product=0x5678,
                )
            except Exception:
                self._close_devices()
                raise

            self._started = True

            for path, dev in self._devices.items():
                thread = threading.Thread(
                    target=self._read_device,
                    args=(path, dev),
                    daemon=True,
                    name=f"input-{os.path.basename(path)}",
                )
                self._threads.append(thread)
                thread.start()

    @staticmethod
    def _is_input_device(caps: dict) -> bool:
        return (
            ecodes.EV_KEY in caps
            or ecodes.EV_REL in caps
            or ecodes.EV_ABS in caps
        )

    def _close_devices(self):
        for dev in self._devices.values():
            try:
                dev.close()
            except Exception:
                pass
        self._devices.clear()

    # ---------------------------------------------------------
    # Hooks
    # ---------------------------------------------------------

    def hook(self, callback: Callable, suppress: bool = False) -> int:
        if not callable(callback):
            raise TypeError("callback must be callable")

        self.start()

        with self._lock:
            handle = self._next_hook_id
            self._next_hook_id += 1
            self._hooks[handle] = (callback, bool(suppress))

            if suppress and not self._suppress_enabled:
                if not self.grab_devices:
                    del self._hooks[handle]
                    raise RuntimeError(
                        "Device grabbing is disabled; suppression is unavailable."
                    )

                self._grab_all()
                self._suppress_enabled = True

            return handle

    def unhook(self, handle: int):
        with self._lock:
            self._hooks.pop(handle, None)

            if not any(s for _, s in self._hooks.values()):
                self._ungrab_all()
                self._suppress_enabled = False

    def unhook_all(self):
        with self._lock:
            self._hooks.clear()
            self._ungrab_all()
            self._suppress_enabled = False

    def _grab_all(self):
        grabbed = []
        try:
            for dev in self._devices.values():
                dev.grab()
                grabbed.append(dev)
        except Exception:
            for dev in grabbed:
                try:
                    dev.ungrab()
                except Exception:
                    pass
            raise RuntimeError(
                "Could not grab all input devices. Check permissions "
                "and whether another program already has an exclusive grab."
            )

    def _ungrab_all(self):
        for dev in self._devices.values():
            try:
                dev.ungrab()
            except Exception:
                pass

    # ---------------------------------------------------------
    # Event reading and dispatch
    # ---------------------------------------------------------

    def _read_device(self, path: str, dev: InputDevice):
        try:
            for raw in dev.read_loop():
                if self._stop.is_set():
                    break

                if raw.type == ecodes.EV_SYN:
                    if raw.code == ecodes.SYN_REPORT:
                        self._relay_syn()
                    continue

                event = self._convert_event(raw, path)
                if event is None:
                    self._relay(raw)
                    continue

                suppress_event = self._dispatch(event)

                if raw.type == ecodes.EV_KEY:
                    name = event.id
                    with self._lock:
                        if raw.value == 1:
                            self._physical_pressed.add(name)
                        elif raw.value == 0:
                            self._physical_pressed.discard(name)

                if not suppress_event:
                    self._relay(raw)

        except (OSError, PermissionError):
            # Device disconnected or access was revoked.
            pass

    def _convert_event(self, raw, path: str) -> InputEvent | None:
        if raw.type == ecodes.EV_KEY:
            code_name = ecodes.KEY.get(raw.code, f"KEY_{raw.code}")
            name = KEY_NAMES.get(code_name, code_name.lower().removeprefix("key_"))

            if raw.value == 1:
                event_type = "down"
            elif raw.value == 0:
                event_type = "up"
            else:
                event_type = "hold"

            device = (
                "mouse" if code_name.startswith("BTN_")
                else "keyboard"
            )

            return InputEvent(
                id=name,
                device=device,
                event_type=event_type,
                scan_code=raw.code,
                injected=False,
                device_id=path,
            )

        if raw.type == ecodes.EV_REL:
            if raw.code == ecodes.REL_X:
                return InputEvent(
                    id="mousemove", device="mouse",
                    event_type="move", x=raw.value,
                    device_id=path,
                )
            if raw.code == ecodes.REL_Y:
                return InputEvent(
                    id="mousemove", device="mouse",
                    event_type="move", y=raw.value,
                    device_id=path,
                )
            if raw.code in (ecodes.REL_WHEEL, ecodes.REL_HWHEEL):
                return InputEvent(
                    id="wheel",
                    device="mouse",
                    event_type="wheel",
                    delta=raw.value,
                    x=raw.value if raw.code == ecodes.REL_HWHEEL else None,
                    y=raw.value if raw.code == ecodes.REL_WHEEL else None,
                    device_id=path,
                )

        return None

    def _dispatch(self, event: InputEvent) -> bool:
        suppress_event = False

        with self._lock:
            hooks = list(self._hooks.values())

        for callback, suppress in hooks:
            try:
                result = callback(event)
                if suppress and result is True:
                    suppress_event = True
            except Exception:
                # Keep the input reader alive if a callback fails.
                continue

        return suppress_event

    def _relay(self, raw):
        if not self._suppress_enabled or self._uinput is None:
            return

        try:
            self._uinput.write(raw.type, raw.code, raw.value)
        except (OSError, ValueError):
            pass

    def _relay_syn(self):
        if not self._suppress_enabled or self._uinput is None:
            return

        try:
            self._uinput.syn()
        except OSError:
            pass

    # ---------------------------------------------------------
    # Synthetic input
    # ---------------------------------------------------------

    def _key_code(self, key: str) -> int:
        name = _normalise(key)

        if name in NAME_TO_CODE and NAME_TO_CODE[name] is not None:
            return NAME_TO_CODE[name]

        raise ValueError(f"Unsupported key: {key!r}")

    def press(self, key: str):
        self.start()
        name = _normalise(key)

        if name in ("wheelup", "wheeldown"):
            self._write_wheel(1 if name == "wheelup" else -1)
            return

        code = self._key_code(name)

        with self._lock:
            if name in self._injected_pressed:
                return
            self._injected_pressed.add(name)

        self._write_event(ecodes.EV_KEY, code, 1)

    def hold(self, key: str):
        self.press(key)

    def release(self, key: str):
        name = _normalise(key)

        if name not in self._injected_pressed:
            return

        code = self._key_code(name)

        with self._lock:
            self._injected_pressed.discard(name)

        self._write_event(ecodes.EV_KEY, code, 0)

    def is_pressed(self, key: str) -> bool:
        name = _normalise(key)
        with self._lock:
            return (
                name in self._injected_pressed
                or name in self._physical_pressed
            )

    def release_all(self):
        with self._lock:
            keys = list(self._injected_pressed)

        for key in keys:
            try:
                self.release(key)
            except (ValueError, OSError):
                pass

    def _write_event(self, event_type: int, code: int, value: int):
        if self._uinput is None:
            raise RuntimeError("Backend is not started")

        self._uinput.write(event_type, code, value)
        self._uinput.syn()

    def _write_wheel(self, direction: int):
        if self._uinput is None:
            self.start()

        # REL_WHEEL: positive is up, negative is down.
        self._uinput.write(ecodes.EV_REL, ecodes.REL_WHEEL, direction)
        self._uinput.syn()

    def write(self, text: str, interval: float = 0):
        self.start()

        shift_code = ecodes.KEY_LEFTSHIFT

        for char in text:
            mapping = CHAR_MAP.get(char)

            if mapping is None:
                raise ValueError(
                    f"Character {char!r} is not supported by the Linux US layout mapping"
                )

            key_name, needs_shift = mapping
            key_code = getattr(ecodes, key_name)

            if needs_shift:
                self._write_event(ecodes.EV_KEY, shift_code, 1)

            self._write_event(ecodes.EV_KEY, key_code, 1)
            self._write_event(ecodes.EV_KEY, key_code, 0)

            if needs_shift:
                self._write_event(ecodes.EV_KEY, shift_code, 0)

            if interval > 0:
                time.sleep(interval)

    # ---------------------------------------------------------
    # Convenience
    # ---------------------------------------------------------

    @contextmanager
    def holding(self, key: str):
        self.press(key)
        try:
            yield
        finally:
            self.release(key)

    def shutdown(self):
        self._stop.set()
        self.release_all()
        self.unhook_all()

        # Closing devices unblocks read loops.
        self._close_devices()

        for thread in self._threads:
            if thread.is_alive():
                thread.join(timeout=0.5)

        self._threads.clear()

        if self._uinput is not None:
            try:
                self._uinput.close()
            except Exception:
                pass
            self._uinput = None

        self._started = False


# Compatibility with the Windows backend import style.
backend = Backend()
