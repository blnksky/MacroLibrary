
import ctypes
import threading
import time

from ctypes import wintypes
from .events import InputEvent


# =========================================================
# Windows API
# =========================================================

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

ULONG_PTR = ctypes.c_size_t

HC_ACTION = 0
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C

LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x10
LLKHF_LOWER_IL_INJECTED = 0x02

LLMHF_INJECTED = 0x01
LLMHF_LOWER_IL_INJECTED = 0x02

INPUT_KEYBOARD = 1
INPUT_MOUSE = 0

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100

WM_MOUSEHWHEEL = 0x020E

MAPVK_VK_TO_VSC_EX = 4

KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002


# =========================================================
# Structures
# =========================================================

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


# =========================================================
# AHK-style key mapping
# =========================================================

VK_KEYS = {
    "esc": 0x1B,
    "tab": 0x09,
    "enter": 0x0D,
    "space": 0x20,
    "backspace": 0x08,

    "home": 0x24,
    "up": 0x26,
    "pgup": 0x21,
    "left": 0x25,
    "right": 0x27,
    "end": 0x23,
    "down": 0x28,
    "pgdn": 0x22,
    "insert": 0x2D,
    "delete": 0x2E,

    "lctrl": 0xA2,
    "rctrl": 0xA3,
    "lshift": 0xA0,
    "rshift": 0xA1,
    "lalt": 0xA4,
    "ralt": 0xA5,

    "capslock": 0x14,
    "numlock": 0x90,
    "scrolllock": 0x91,

    "lwin": 0x5B,
    "rwin": 0x5C,
    "appskey": 0x5D,
}

for i in range(10):
    VK_KEYS[str(i)] = 0x30 + i

for i, char in enumerate("abcdefghijklmnopqrstuvwxyz"):
    VK_KEYS[char] = ord(char.upper())

for i in range(1, 25):
    VK_KEYS[f"f{i}"] = 0x70 + i - 1


KEY_NAMES = {value: key for key, value in VK_KEYS.items()}

IIDS = set(KEY_NAMES.values())

MOUSE_BUTTONS = {
    "lbutton": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "rbutton": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "mbutton": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
    "xbutton1": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP),
    "xbutton2": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP),
}


# =========================================================
# Injection
# =========================================================

def _send_input(event):
    result = user32.SendInput(
        1,
        ctypes.byref(event),
        ctypes.sizeof(INPUT)
    )

    if result != 1:
        raise ctypes.WinError(ctypes.get_last_error())


def _keyboard_input(key, key_up=False):
    vk = VK_KEYS.get(key.lower())

    if vk is None:
        raise ValueError(f"Unknown key: {key}")

    scan_code = user32.MapVirtualKeyW(vk, 4)

    flags = KEYEVENTF_SCANCODE

    if key_up:
        flags |= KEYEVENTF_KEYUP

    # Extended keys
    if vk in {
        0x21,  # Page Up
        0x22,  # Page Down
        0x23,  # End
        0x24,  # Home
        0x25,  # Left
        0x26,  # Up
        0x27,  # Right
        0x28,  # Down
        0x2D,  # Insert
        0x2E,  # Delete
        0x5B,  # Left Windows
        0x5C,  # Right Windows
        0x5D,  # Applications
    }:
        flags |= KEYEVENTF_EXTENDEDKEY

    event = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(
            wVk=0,
            wScan=scan_code,
            dwFlags=flags,
            time=0,
            dwExtraInfo=0,
        ),
    )

    _send_input(event)


_held = set()
_held_lock = threading.RLock()


def press(identifier):
    identifier = identifier.lower()

    with _held_lock:
        if identifier in _held:
            return

        if identifier in MOUSE_BUTTONS:
            down, _ = MOUSE_BUTTONS[identifier]
            data = 2 if identifier == "xbutton2" else 1

            event = INPUT(
                type=INPUT_MOUSE,
                mi=MOUSEINPUT(0, 0, data, down, 0, 0)
            )
            _send_input(event)
        else:
            _keyboard_input(identifier)

        _held.add(identifier)


def release(identifier):
    identifier = identifier.lower()

    with _held_lock:
        if identifier not in _held:
            return

        if identifier in MOUSE_BUTTONS:
            _, up = MOUSE_BUTTONS[identifier]
            data = 2 if identifier == "xbutton2" else 1

            event = INPUT(
                type=INPUT_MOUSE,
                mi=MOUSEINPUT(0, 0, data, up, 0, 0)
            )
            _send_input(event)
        else:
            _keyboard_input(identifier, key_up=True)

        _held.discard(identifier)


def hold(identifier):
    press(identifier)


def is_pressed(identifier):
    with _held_lock:
        return identifier.lower() in _held


def release_all():
    with _held_lock:
        identifiers = list(_held)

    for identifier in identifiers:
        release(identifier)


# =========================================================
# Event hooks
# =========================================================

_callbacks = {}
_hook_thread = None
_hook_ready = threading.Event()
_hook_lock = threading.RLock()


def _keyboard_callback(nCode, wParam, lParam):
    if nCode == HC_ACTION:
        data = ctypes.cast(
            lParam,
            ctypes.POINTER(KBDLLHOOKSTRUCT)
        ).contents

        down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
        up = wParam in (WM_KEYUP, WM_SYSKEYUP)

        if down or up:
            # Distinguish dedicated navigation keys from numpad keys.
            extended = bool(data.flags & LLKHF_EXTENDED)

            if data.vkCode == 0x0D and extended:
                name = "numpadenter"
            else:
                name = KEY_NAMES.get(
                    data.vkCode,
                    f"vk_{data.vkCode:02x}"
                )

            event = InputEvent(
                id=name,
                device="keyboard",
                event_type="down" if down else "up",
                scan_code=data.scanCode,
                vk_code=data.vkCode,
                injected=bool(
                    data.flags & (LLKHF_INJECTED | LLKHF_LOWER_IL_INJECTED)
                ),
            )

            if _dispatch(event):
                return 1

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


def _mouse_callback(nCode, wParam, lParam):
    if nCode == HC_ACTION:
        data = ctypes.cast(
            lParam,
            ctypes.POINTER(MSLLHOOKSTRUCT)
        ).contents

        names = {
            WM_LBUTTONDOWN: ("lbutton", "down"),
            WM_LBUTTONUP: ("lbutton", "up"),
            WM_RBUTTONDOWN: ("rbutton", "down"),
            WM_RBUTTONUP: ("rbutton", "up"),
            WM_MBUTTONDOWN: ("mbutton", "down"),
            WM_MBUTTONUP: ("mbutton", "up"),
            WM_MOUSEMOVE: ("mousemove", "move"),
            WM_MOUSEWHEEL: ("hwheel", "wheel"),
            WM_XBUTTONDOWN: ("xbutton", "down"),
            WM_XBUTTONUP: ("xbutton", "up"),
        }

        if wParam in names:
            name, event_type = names[wParam]

            if wParam in (WM_XBUTTONDOWN, WM_XBUTTONUP):
                button = (data.mouseData >> 16) & 0xFFFF
                name = "xbutton1" if button == 1 else "xbutton2"

            event = InputEvent(
                id=name,
                device="mouse",
                event_type=event_type,
                x=data.pt.x,
                y=data.pt.y,
                delta=(
                    ctypes.c_short(data.mouseData >> 16).value
                    if wParam in (WM_MOUSEWHEEL, WM_MOUSEHWHEEL)
                    else None
                ),
                injected=bool(
                    data.flags & (LLMHF_INJECTED | LLMHF_LOWER_IL_INJECTED)
                ),
            )

            if _dispatch(event):
                return 1

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


def _dispatch(event):
    with _hook_lock:
        callbacks = list(_callbacks.values())

    for callback, suppress in callbacks:
        try:
            result = callback(event)

            if suppress and result is True:
                return True

        except Exception:
            pass

    return False


# Keep callback objects alive.
_KEYBOARD_PROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM
)(_keyboard_callback)

_MOUSE_PROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM
)(_mouse_callback)


# =========================================================
# Hook message loop
# =========================================================

def _hook_loop():
    keyboard_hook = None
    mouse_hook = None

    try:
        keyboard_hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            _KEYBOARD_PROC,
            None,
            0
        )

        if not keyboard_hook:
            raise ctypes.WinError(ctypes.get_last_error())

        mouse_hook = user32.SetWindowsHookExW(
            WH_MOUSE_LL,
            _MOUSE_PROC,
            None,
            0
        )

        if not mouse_hook:
            raise ctypes.WinError(ctypes.get_last_error())

        _hook_ready.set()

        msg = wintypes.MSG()

        while True:
            result = user32.GetMessageW(
                ctypes.byref(msg), None, 0, 0
            )

            if result <= 0:
                break

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    except Exception as exc:
        _hook_error.append(exc)
        _hook_ready.set()

    finally:
        if keyboard_hook:
            user32.UnhookWindowsHookEx(keyboard_hook)

        if mouse_hook:
            user32.UnhookWindowsHookEx(mouse_hook)


# =========================================================
# Public backend interface
# =========================================================

_hook_error = []

def start():
    global _hook_thread

    if _hook_thread and _hook_thread.is_alive():
        return

    _hook_ready.clear()
    _hook_error.clear()

    _hook_thread = threading.Thread(
        target=_hook_loop,
        daemon=True
    )
    _hook_thread.start()

    if not _hook_ready.wait(timeout=5):
        raise RuntimeError("Windows hook initialization timed out.")

    if _hook_error:
        raise RuntimeError("Windows hook initialization failed.") from _hook_error[0]


def hook(callback, suppress=False):
    start()

    handle = object()

    with _hook_lock:
        _callbacks[handle] = (callback, suppress)

    return handle


def unhook(handle):
    with _hook_lock:
        _callbacks.pop(handle, None)


def write(text: str, interval: float = 0):
    import time

    for char in text:
        code = ord(char)

        units = (
            [code] if code <= 0xFFFF else [
                0xD800 + ((code - 0x10000) >> 10),
                0xDC00 + ((code - 0x10000) & 0x3FF),
            ]
        )

        for unit in units:
            for key_up in (False, True):
                flags = KEYEVENTF_UNICODE
                if key_up:
                    flags |= KEYEVENTF_KEYUP

                event = INPUT(
                    type=INPUT_KEYBOARD,
                    ki=KEYBDINPUT(
                        wVk=0,
                        wScan=unit,
                        dwFlags=flags,
                        time=0,
                        dwExtraInfo=0,
                    )
                )
                _send_input(event)

        if interval > 0:
            time.sleep(interval)
