"""
Windows backend (ctypes + low level hooks + SendInput).

Compared to the previous implementation this fixes:

* complete key coverage (numpad, punctuation, PrintScreen, media ...),
* extended scan codes (RAlt/RCtrl/NumpadEnter/...) via KEYEVENTF_EXTENDEDKEY,
* mouse buttons, wheel and pointer movement,
* physical ``is_pressed`` via GetAsyncKeyState,
* self-injection tagging and a proper hook-thread shutdown.
"""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes

from .. import keymap
from ..events import InputEvent
from ._win32 import (
    HC_ACTION,
    INPUT,
    INPUT_KEYBOARD,
    INPUT_MOUSE,
    KBDLLHOOKSTRUCT,
    KEYBDINPUT,
    KEYEVENTF_EXTENDEDKEY,
    KEYEVENTF_KEYUP,
    KEYEVENTF_UNICODE,
    LLKHF_EXTENDED,
    LLKHF_INJECTED,
    LLKHF_LOWER_IL_INJECTED,
    LLMHF_INJECTED,
    LLMHF_LOWER_IL_INJECTED,
    MLIB_TAG,
    MOUSEINPUT,
    MOUSEEVENTF_HWHEEL,
    MOUSEEVENTF_LEFTDOWN,
    MOUSEEVENTF_LEFTUP,
    MOUSEEVENTF_MIDDLEDOWN,
    MOUSEEVENTF_MIDDLEUP,
    MOUSEEVENTF_MOVE,
    MOUSEEVENTF_RIGHTDOWN,
    MOUSEEVENTF_RIGHTUP,
    MOUSEEVENTF_WHEEL,
    MOUSEEVENTF_XDOWN,
    MOUSEEVENTF_XUP,
    MSLLHOOKSTRUCT,
    POINT,
    WM_KEYDOWN,
    WM_KEYUP,
    WM_LBUTTONDOWN,
    WM_LBUTTONUP,
    WM_MBUTTONDOWN,
    WM_MBUTTONUP,
    WM_MOUSEHWHEEL,
    WM_MOUSEMOVE,
    WM_MOUSEWHEEL,
    WM_QUIT,
    WM_RBUTTONDOWN,
    WM_RBUTTONUP,
    WM_SYSKEYDOWN,
    WM_SYSKEYUP,
    WM_XBUTTONDOWN,
    WM_XBUTTONUP,
    WH_KEYBOARD_LL,
    WH_MOUSE_LL,
    HOOKPROC,
    kernel32,
    user32,
)
from .contract import Backend

__all__ = ["WindowsBackend"]

_BUTTON_FLAGS = {
    "lbutton": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "rbutton": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "mbutton": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
    "xbutton1": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP),
    "xbutton2": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP),
}
_XBUTTON_DATA = {"xbutton1": 1, "xbutton2": 2}

_MOUSE_DOWN = {
    WM_LBUTTONDOWN: ("lbutton", "down"),
    WM_LBUTTONUP: ("lbutton", "up"),
    WM_RBUTTONDOWN: ("rbutton", "down"),
    WM_RBUTTONUP: ("rbutton", "up"),
    WM_MBUTTONDOWN: ("mbutton", "down"),
    WM_MBUTTONUP: ("mbutton", "up"),
}


def _win_error(message: str) -> OSError:
    return ctypes.WinError(ctypes.get_last_error())


class WindowsBackend(Backend):
    def __init__(self) -> None:
        super().__init__()
        self._hook_thread: threading.Thread | None = None
        self._hook_thread_id: int | None = None
        self._hook_ready = threading.Event()
        self._hook_error: BaseException | None = None
        self._lifecycle_lock = threading.RLock()
        self._kb_proc = HOOKPROC(self._keyboard_callback)
        self._ms_proc = HOOKPROC(self._mouse_callback)

    # ------------------------------------------------------------------
    # Injection
    # ------------------------------------------------------------------

    @staticmethod
    def _send_inputs(*inputs: INPUT) -> None:
        array = (INPUT * len(inputs))(*inputs)
        sent = user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            raise _win_error("SendInput failed")

    def _key_input(self, spec: keymap.KeySpec, up: bool) -> INPUT:
        vk = spec.vk
        if not vk:
            raise ValueError(f"No virtual-key code for {spec.id!r}")

        flags = KEYEVENTF_EXTENDEDKEY if spec.extended else 0
        if up:
            flags |= KEYEVENTF_KEYUP

        return INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=MLIB_TAG),
        )

    def _mouse_input(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> INPUT:
        return INPUT(
            type=INPUT_MOUSE,
            mi=MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, MLIB_TAG),
        )

    def _mouse_button(self, identifier: str, down: bool) -> None:
        down_flag, up_flag = _BUTTON_FLAGS[identifier]
        flags = down_flag if down else up_flag
        data = _XBUTTON_DATA.get(identifier, 0)
        self._send_inputs(self._mouse_input(flags, data=data))

    def _press(self, spec: keymap.KeySpec) -> None:
        if spec.kind == "button":
            self._mouse_button(spec.id, True)
        elif spec.id == "mousemove":
            return
        else:
            self._send_inputs(self._key_input(spec, up=False))

    def _release(self, spec: keymap.KeySpec) -> None:
        if spec.kind == "button":
            self._mouse_button(spec.id, False)
        elif spec.id == "mousemove":
            return
        else:
            self._send_inputs(self._key_input(spec, up=True))

    def _wheel(self, axis: str, direction: int) -> None:
        if not direction:
            return
        delta = direction * 120
        if axis == "x":
            self._send_inputs(self._mouse_input(MOUSEEVENTF_HWHEEL, data=ctypes.c_uint32(delta).value))
        else:
            self._send_inputs(self._mouse_input(MOUSEEVENTF_WHEEL, data=ctypes.c_uint32(delta).value))

    def _move(self, x: int, y: int, absolute: bool) -> None:
        if absolute:
            if not user32.SetCursorPos(x, y):
                raise _win_error("SetCursorPos failed")
        else:
            self._send_inputs(self._mouse_input(MOUSEEVENTF_MOVE, dx=x, dy=y))

    def _get_position(self) -> tuple[int, int]:
        point = POINT()
        if not user32.GetCursorPos(ctypes.byref(point)):
            raise _win_error("GetCursorPos failed")
        return (point.x, point.y)

    def _write(self, text: str, interval: float) -> None:
        for char in text:
            code = ord(char)
            units = [code] if code <= 0xFFFF else [
                0xD800 + ((code - 0x10000) >> 10),
                0xDC00 + ((code - 0x10000) & 0x3FF),
            ]
            for unit in units:
                for up in (False, True):
                    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
                    self._send_inputs(
                        INPUT(
                            type=INPUT_KEYBOARD,
                            ki=KEYBDINPUT(wVk=0, wScan=unit, dwFlags=flags, time=0, dwExtraInfo=MLIB_TAG),
                        )
                    )
            if interval > 0:
                time.sleep(interval)

    def _is_physically_pressed(self, spec: keymap.KeySpec) -> bool:
        if spec.kind == "button":
            vk = keymap.MOUSE_VK.get(spec.id)
        else:
            vk = spec.vk
        if not vk:
            return False
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def _keyboard_callback(self, n_code, w_param, l_param):
        if n_code == HC_ACTION:
            data = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            down = w_param in (WM_KEYDOWN, WM_SYSKEYDOWN)
            up = w_param in (WM_KEYUP, WM_SYSKEYUP)
            if down or up:
                extended = bool(data.flags & LLKHF_EXTENDED)
                vk = int(data.vkCode)

                if vk == 0x0D and extended:
                    identifier = "numpadenter"
                else:
                    identifier = keymap.BY_VK.get(vk, f"vk_{vk:02x}")

                event = InputEvent(
                    id=identifier,
                    device="keyboard",
                    event_type="down" if down else "up",
                    scan_code=int(data.scanCode),
                    vk_code=vk,
                    injected=bool(data.flags & (LLKHF_INJECTED | LLKHF_LOWER_IL_INJECTED))
                    or int(data.dwExtraInfo) == MLIB_TAG,
                )
                if self._dispatch(event):
                    return 1
        return user32.CallNextHookEx(None, n_code, w_param, l_param)

    def _mouse_callback(self, n_code, w_param, l_param):
        if n_code == HC_ACTION:
            data = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            injected = (
                bool(data.flags & (LLMHF_INJECTED | LLMHF_LOWER_IL_INJECTED))
                or int(data.dwExtraInfo) == MLIB_TAG
            )
            event: InputEvent | None = None

            if w_param in _MOUSE_DOWN:
                identifier, event_type = _MOUSE_DOWN[w_param]
                event = InputEvent(
                    id=identifier,
                    device="mouse",
                    event_type=event_type,
                    x=data.pt.x,
                    y=data.pt.y,
                    injected=injected,
                )

            elif w_param in (WM_XBUTTONDOWN, WM_XBUTTONUP):
                button = (int(data.mouseData) >> 16) & 0xFFFF
                identifier = "xbutton1" if button == 1 else "xbutton2"
                event = InputEvent(
                    id=identifier,
                    device="mouse",
                    event_type="down" if w_param == WM_XBUTTONDOWN else "up",
                    x=data.pt.x,
                    y=data.pt.y,
                    injected=injected,
                )

            elif w_param == WM_MOUSEMOVE:
                event = InputEvent(
                    id="mousemove",
                    device="mouse",
                    event_type="move",
                    x=data.pt.x,
                    y=data.pt.y,
                    injected=injected,
                )

            elif w_param in (WM_MOUSEWHEEL, WM_MOUSEHWHEEL):
                delta = ctypes.c_short((int(data.mouseData) >> 16) & 0xFFFF).value
                if w_param == WM_MOUSEWHEEL:
                    identifier = "wheelup" if delta > 0 else "wheeldown"
                else:
                    identifier = "wheelright" if delta > 0 else "wheelleft"
                event = InputEvent(
                    id=identifier,
                    device="mouse",
                    event_type="wheel",
                    x=data.pt.x,
                    y=data.pt.y,
                    delta=delta,
                    injected=injected,
                )

            if event is not None and self._dispatch(event):
                return 1
        return user32.CallNextHookEx(None, n_code, w_param, l_param)

    # ------------------------------------------------------------------
    # Hook thread
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._hook_thread is not None and self._hook_thread.is_alive():
                return
            self._hook_ready.clear()
            self._hook_error = None
            self._hook_thread = threading.Thread(
                target=self._hook_loop,
                name="windows-input-hook",
                daemon=True,
            )
            self._hook_thread.start()

        if not self._hook_ready.wait(5):
            raise RuntimeError("Windows hook initialization timed out.")
        if self._hook_error is not None:
            raise RuntimeError("Windows hook initialization failed.") from self._hook_error

    def _hook_loop(self) -> None:
        keyboard_hook = None
        mouse_hook = None
        try:
            keyboard_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kb_proc, None, 0)
            if not keyboard_hook:
                raise _win_error("SetWindowsHookExW(WH_KEYBOARD_LL) failed")

            mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._ms_proc, None, 0)
            if not mouse_hook:
                raise _win_error("SetWindowsHookExW(WH_MOUSE_LL) failed")

            self._hook_thread_id = int(kernel32.GetCurrentThreadId())
            self._hook_ready.set()

            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except BaseException as exc:
            self._hook_error = exc
            self._hook_ready.set()
        finally:
            if keyboard_hook:
                user32.UnhookWindowsHookEx(keyboard_hook)
            if mouse_hook:
                user32.UnhookWindowsHookEx(mouse_hook)

    def _on_idle(self) -> None:
        with self._lifecycle_lock:
            thread_id = self._hook_thread_id
            thread = self._hook_thread
            if thread is not None and thread.is_alive() and thread_id:
                user32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
                if threading.current_thread() is not thread:
                    thread.join(timeout=2)
            if threading.current_thread() is not thread:
                self._hook_thread = None
                self._hook_thread_id = None

    def shutdown(self) -> None:
        super().shutdown()
        self._on_idle()
