"""
Linux backend (evdev + uinput).

It implements exactly the same :class:`Backend` contract as the Windows one.
evdev is imported lazily so the rest of the package (and this module) can be
imported on any platform.
"""

from __future__ import annotations

import os
import threading
import time

from .. import keymap
from ..events import InputEvent
from .contract import Backend

__all__ = ["LinuxBackend"]


class LinuxBackend(Backend):
    def __init__(self, grab_devices: bool = True) -> None:
        super().__init__()
        self.grab_devices = grab_devices
        self._lifecycle = threading.RLock()
        self._stop = threading.Event()

        self._devices: dict[str, object] = {}
        self._threads: list[threading.Thread] = []
        self._uinput = None
        self._started = False
        self._grabbed = False

        self._ecodes = None
        self._name_to_code: dict[str, int] = {}
        self._linux_to_id: dict[str, str] = {}
        self._code_to_id: dict[int, str] = {}
        self._code_to_device: dict[int, str] = {}

        self._physical: set[str] = set()
        self._position = [0, 0]

    # ------------------------------------------------------------------
    # Lazy evdev
    # ------------------------------------------------------------------

    def _load_evdev(self):
        if self._ecodes is None:
            from evdev import ecodes

            self._ecodes = ecodes
            for spec in keymap._SPECS.values():  # noqa: SLF001 - single source of truth
                if not spec.linux:
                    continue
                code = getattr(ecodes, spec.linux, None)
                if code is None:
                    continue
                self._name_to_code[spec.id] = code
                self._linux_to_id[spec.linux] = spec.id
                self._code_to_id.setdefault(code, spec.id)
                self._code_to_device.setdefault(code, "mouse" if spec.linux.startswith("BTN_") else "keyboard")

    def start(self) -> None:
        self._load_evdev()

        with self._lifecycle:
            if self._started:
                return

            from evdev import InputDevice, UInput, list_devices

            capabilities: dict[int, list[int]] = {}
            for path in list_devices():
                try:
                    device = InputDevice(path)
                    caps = device.capabilities()
                    if not (self._ecodes.EV_KEY in caps or self._ecodes.EV_REL in caps or self._ecodes.EV_ABS in caps):
                        device.close()
                        continue

                    if device.name == "MacroLibrary Virtual Input":
                        device.close()
                        continue

                    self._devices[path] = device
                    for event_type, codes in caps.items():
                        if event_type in (self._ecodes.EV_SYN, self._ecodes.EV_FF, self._ecodes.EV_PWR):
                            continue
                        existing = set(capabilities.get(event_type, []))
                        existing.update(code for code in codes if isinstance(code, int))
                        capabilities[event_type] = sorted(existing)
                except (OSError, PermissionError):
                    continue

            if not self._devices:
                raise RuntimeError("No readable input devices found. Check /dev/input permissions.")

            try:
                self._uinput = UInput(
                    events=capabilities,
                    name="MacroLibrary Virtual Input",
                    vendor=0x1234,
                    product=0x5678,
                )
            except Exception:
                self._close_devices()
                raise

            self._started = True
            self._stop.clear()

            for path, device in self._devices.items():
                thread = threading.Thread(
                    target=self._read_device,
                    args=(path, device),
                    name=f"input-{os.path.basename(path)}",
                    daemon=True,
                )
                self._threads.append(thread)
                thread.start()

    def _close_devices(self) -> None:
        for device in self._devices.values():
            try:
                device.close()
            except Exception:
                pass
        self._devices.clear()

    # ------------------------------------------------------------------
    # Injection
    # ------------------------------------------------------------------

    def _code(self, spec: keymap.KeySpec) -> int:
        self._load_evdev()
        code = self._name_to_code.get(spec.id)
        if code is None:
            raise ValueError(f"Unsupported Linux key: {spec.id!r}")
        return code

    def _write_event(self, event_type: int, code: int, value: int) -> None:
        if self._uinput is None:
            self.start()
        self._uinput.write(event_type, code, value)
        self._uinput.syn()

    def _press(self, spec: keymap.KeySpec) -> None:
        self._load_evdev()
        if spec.kind == "button":
            self._write_event(self._ecodes.EV_KEY, self._code(spec), 1)
        elif spec.id == "mousemove":
            return
        else:
            self._write_event(self._ecodes.EV_KEY, self._code(spec), 1)

    def _release(self, spec: keymap.KeySpec) -> None:
        self._load_evdev()
        if spec.kind == "button":
            self._write_event(self._ecodes.EV_KEY, self._code(spec), 0)
        elif spec.id == "mousemove":
            return
        else:
            self._write_event(self._ecodes.EV_KEY, self._code(spec), 0)

    def _wheel(self, axis: str, direction: int) -> None:
        if not direction:
            return
        self._load_evdev()
        code = self._ecodes.REL_HWHEEL if axis == "x" else self._ecodes.REL_WHEEL
        self._write_event(self._ecodes.EV_REL, code, direction)

    def _move(self, x: int, y: int, absolute: bool) -> None:
        if absolute:
            raise NotImplementedError(
                "Absolute pointer movement is not available through evdev/uinput. "
                "Use relative movement, or an XTest/ydotool backend on X11/Wayland."
            )
        self._load_evdev()
        if x:
            self._write_event(self._ecodes.EV_REL, self._ecodes.REL_X, int(x))
        if y:
            self._write_event(self._ecodes.EV_REL, self._ecodes.REL_Y, int(y))

    def _get_position(self) -> tuple[int, int]:
        return (self._position[0], self._position[1])

    def _write(self, text: str, interval: float) -> None:
        self._load_evdev()
        shift = self._ecodes.KEY_LEFTSHIFT

        for char in text:
            mapping = keymap.CHAR_MAP.get(char)
            if mapping is None:
                raise ValueError(f"Character {char!r} is not supported by the Linux US layout mapping")

            key_name, needs_shift = mapping
            identifier = self._linux_to_id.get(key_name, keymap.normalize(key_name))
            code = self._name_to_code.get(identifier)

            if code is None:
                raise ValueError(f"No evdev code for {key_name!r}")

            if needs_shift:
                self._write_event(self._ecodes.EV_KEY, shift, 1)
            self._write_event(self._ecodes.EV_KEY, code, 1)
            self._write_event(self._ecodes.EV_KEY, code, 0)
            if needs_shift:
                self._write_event(self._ecodes.EV_KEY, shift, 0)

            if interval > 0:
                time.sleep(interval)

    def _is_physically_pressed(self, spec: keymap.KeySpec) -> bool:
        with self._lock:
            return spec.id in self._physical

    # ------------------------------------------------------------------
    # Reading / relaying
    # ------------------------------------------------------------------

    def _read_device(self, path: str, device) -> None:
        try:
            for raw in device.read_loop():
                if self._stop.is_set():
                    break

                if raw.type == self._ecodes.EV_SYN:
                    if raw.code == self._ecodes.SYN_REPORT and self._grabbed and self._uinput is not None:
                        try:
                            self._uinput.syn()
                        except OSError:
                            pass
                    continue

                event = self._convert(raw, path)

                if event is None:
                    if self._grabbed:
                        self._relay(raw)
                    continue

                if event.event_type in ("down", "up"):
                    with self._lock:
                        if event.event_type == "down":
                            self._physical.add(event.id)
                        else:
                            self._physical.discard(event.id)

                if event.kind == "move":
                    if event.x is not None:
                        self._position[0] += int(event.x)
                    if event.y is not None:
                        self._position[1] += int(event.y)

                suppressed = self._dispatch(event)
                if self._grabbed and not suppressed:
                    self._relay(raw)
        except (OSError, PermissionError):
            return

    def _relay(self, raw) -> None:
        if self._uinput is None:
            return
        try:
            self._uinput.write(raw.type, raw.code, raw.value)
        except (OSError, ValueError):
            pass

    def _convert(self, raw, path: str) -> InputEvent | None:
        ecodes = self._ecodes

        if raw.type == ecodes.EV_KEY:
            device = self._code_to_device.get(raw.code, "keyboard")
            identifier = self._code_to_id.get(raw.code)
            if identifier is None:
                return None
            event_type = "down" if raw.value == 1 else "up" if raw.value == 0 else "repeat"
            return InputEvent(
                id=identifier,
                device=device,
                event_type=event_type,
                scan_code=raw.code,
                device_id=path,
            )

        if raw.type == ecodes.EV_REL:
            if raw.code in (ecodes.REL_X, ecodes.REL_Y):
                return InputEvent(
                    id="mousemove",
                    device="mouse",
                    event_type="move",
                    x=raw.value if raw.code == ecodes.REL_X else None,
                    y=raw.value if raw.code == ecodes.REL_Y else None,
                    device_id=path,
                )
            if raw.code == ecodes.REL_WHEEL:
                return InputEvent(
                    id="wheelup" if raw.value > 0 else "wheeldown",
                    device="mouse",
                    event_type="wheel",
                    delta=raw.value,
                    y=raw.value,
                    device_id=path,
                )
            if raw.code == ecodes.REL_HWHEEL:
                return InputEvent(
                    id="wheelright" if raw.value > 0 else "wheelleft",
                    device="mouse",
                    event_type="wheel",
                    delta=raw.value,
                    x=raw.value,
                    device_id=path,
                )

        return None

    # ------------------------------------------------------------------
    # Grabbing (suppression)
    # ------------------------------------------------------------------

    def _grab_all(self) -> None:
        grabbed = []
        try:
            for device in self._devices.values():
                device.grab()
                grabbed.append(device)
        except Exception:
            for device in grabbed:
                try:
                    device.ungrab()
                except Exception:
                    pass
            raise RuntimeError(
                "Could not grab all input devices. Check permissions and whether "
                "another program already holds an exclusive grab."
            )

    def _ungrab_all(self) -> None:
        for device in self._devices.values():
            try:
                device.ungrab()
            except Exception:
                pass

    def _on_hooks_changed(self) -> None:
        with self._hooks_lock:
            need = any(blocking for _, blocking in self._hooks.values())

        if need and not self._grabbed:
            if not self.grab_devices:
                raise RuntimeError("Device grabbing is disabled; suppression is unavailable.")
            self._load_evdev()
            self._grab_all()
            self._grabbed = True
        elif not need and self._grabbed:
            self._ungrab_all()
            self._grabbed = False

    def _on_idle(self) -> None:
        if self._grabbed:
            self._ungrab_all()
            self._grabbed = False

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        super().shutdown()
        self._stop.set()
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
