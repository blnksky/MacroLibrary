"""
High level runtime: bindings, state, session, macros.

One ``InputRuntime`` owns everything that used to be module-level globals in
``base.py`` (``inputStates``, ``rebinds``, ``inputQueue``, ...). ``base.py`` is
now a thin facade over this object.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

from ..common import delay, sleep
from ..Structures import Event
from . import backend as uin
from . import keymap
from .binding import Bind, Connection, Registry
from .dispatch import Dispatcher
from .events import InputEvent
from .session import Session
from .state import InputState

__all__ = ["InputRuntime", "runtime"]


class InputRuntime:
    def __init__(self, backend=None) -> None:
        self.backend = backend if backend is not None else uin.backend
        self.state = InputState(buffer=100)
        self.registry = Registry()
        Bind.registry = self.registry

        self.dispatcher = Dispatcher(self)
        self.session = Session(self)
        self.enabled = self.session.active

        self.hotkeyBuffer: int = 100
        self.bufferDuration: int = 150
        self.bufferInterval: int = 25

        self.remaps: dict[tuple[str, ...], Any] = {}

        # Compatibility events (``Input.send.connect(...)``).
        self.send = Event(self._send)
        self.down = Event(lambda id: None)
        self.up = Event(lambda id: None)

        self._buffer_stops: dict[int, threading.Event] = {}

    # ------------------------------------------------------------------
    # Low level passthrough
    # ------------------------------------------------------------------

    def press(self, identifier: str, device: str | None = None) -> None:
        self.backend.press(self.backend_id(identifier, device))

    def release(self, identifier: str, device: str | None = None) -> None:
        self.backend.release(self.backend_id(identifier, device))

    def hold(self, identifier: str, device: str | None = None) -> None:
        self.backend.hold(self.backend_id(identifier, device))

    def is_pressed(self, identifier: str, device: str | None = None) -> bool:
        return self.backend.is_pressed(self.backend_id(identifier, device))

    def backend_id(self, identifier: str, device: str | None = None) -> str:
        return keymap.spec(identifier, device=device).id

    def write(self, text: str, interval: float = 0.0) -> None:
        self.backend.write(text, interval)

    def release_all(self) -> None:
        self.backend.release_all()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get(self, input) -> bool:
        return self.state.get(input)

    def last(self, identifier: str, state: bool | None = None):
        return self.state.last(identifier, state)

    def wait(self, identifier: str, timeout: int | None = None, pressed: bool | None = None) -> bool:
        return self.state.wait(identifier, timeout, pressed)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def _send(
        self,
        input,
        state: bool | None = None,
        rebind: bool = False,
        stateDelay: int | None = None,
    ) -> bool:
        sig = keymap.parse(input)

        if rebind or sig.rebind:
            mapped = self.remaps.get(sig.ids)
            if mapped is not None:
                return self._send(mapped, state, False, stateDelay)

        if sig.text is not None:
            self.backend.write(sig.text)
            return True

        if not sig.ids:
            return False

        if state is None and sig.state is not None:
            state = sig.state

        if len(sig.ids) == 1:
            identifier = sig.ids[0]
            if state is True:
                self.backend.press(identifier)
            elif state is False:
                self.backend.release(identifier)
            else:
                self.backend.press(identifier)
                if stateDelay:
                    sleep(stateDelay)
                self.backend.release(identifier)
            return True

        if state is True:
            for identifier in sig.ids:
                self.backend.press(identifier)
        elif state is False:
            for identifier in reversed(sig.ids):
                self.backend.release(identifier)
        else:
            # Modifiers first, released in reverse order.
            for identifier in sig.ids:
                self.backend.press(identifier)
            if stateDelay:
                sleep(stateDelay)
            for identifier in reversed(sig.ids):
                self.backend.release(identifier)
        return True

    def send_sync(self, input, state: bool | None = None, rebind: bool = False, stateDelay: int | None = None) -> bool:
        """Call the send guard directly, bypassing the Event fan-out."""
        return self._send(input, state, rebind, stateDelay)

    def resolve(self, input) -> None:
        sig = keymap.parse(input)
        for identifier in sig.ids:
            self.send(identifier , self.state.pressed(identifier))

    def toggle(self, id: str, timeout: int = 0) -> None:
        sig = keymap.parse(id)
        if not sig.ids:
            return
        target = sig.state if sig.state is not None else True
        first = sig.ids[0]

        self.send(id if sig.state is not None else id + " down")

        if timeout <= 0:
            if self.state.pressed(first) != target:
                self.resolve(id)
            return

        def later() -> None:
            self.state.wait(first, timeout, not target)
            sleep(timeout)
            self.resolve(id)

        delay(later)

    def trigger(self, id: str, delay: int = 0) -> None:
        sig = keymap.parse(id)
        if not sig.ids:
            return
        target = sig.state if sig.state is not None else True
        self._send((", ".join(sig.ids)) + (" up" if target else " down"))
        sleep(delay)
        self.send(id)

    # ------------------------------------------------------------------
    # Binding
    # ------------------------------------------------------------------

    def bind(self, input, call, *, block: bool | None = None, enabled: bool = True, always: bool = False) -> Bind:
        return Bind(input, call, block=block, enabled=enabled, always=always, registry=self.registry)

    def rebind(self, input, output) -> Bind:
        sig = keymap.parse(input, bind=True)
        if not sig.ids:
            raise ValueError("Cannot rebind literal text.")

        # ``~`` passthrough must survive the re-bind; ``sig.ids`` no longer
        # carries the marker, so the block flag is passed explicitly.
        block = not sig.passthrough
        out_sig = keymap.parse(output)

        # Literal text and explicit " down"/" up" inputs tap the output once,
        # matching the historical implementation.
        if out_sig.text is not None or sig.state is not None:
            def on_tap(event_id: str) -> None:
                self.send(output)

            return self.bind(input, on_tap, block=block)

        # A plain key rebind mirrors the output's pressed/released state for as
        # long as the input is held.
        def on_down(event_id: str) -> None:
            self.send(output, True)

        def on_up(event_id: str) -> None:
            self.send(output, False)

        down = self.bind(sig.ids, on_down, block=block)
        up = self.bind(", ".join(sig.ids) + " up", on_up, block=block)
        down.pair = up

        if out_sig.ids:
            self.remaps[sig.ids] = out_sig.ids

        return down

    def bind_buffer(self, inp, duration: int | None = None, interval: int | None = None) -> Bind:
        duration = self.bufferDuration if duration is None else duration
        interval = self.bufferInterval if interval is None else interval
        active = threading.Event()

        def repeat() -> None:
            while active.is_set():
                self._send(inp, rebind=True)
                sleep(interval)

        def on_down(event_id: str) -> None:
            if active.is_set():
                return
            active.set()
            threading.Thread(target=repeat, name="input-buffer", daemon=True).start()
            self.state.wait(keymap.parse(inp).ids[0], None, False)
            if duration > 0:
                sleep(duration)
            active.clear()

        sig = keymap.parse(inp, bind=True)
        return self.bind(("~" + ", ".join(sig.ids)), on_down)

    def simulate(self, id: str) -> None:
        sig = keymap.parse(id)

        def fire(event: InputEvent) -> None:
            self.state.track(event)
            self.registry.dispatch(event, self.state, None)

        for identifier in sig.ids:
            if sig.state in (None, True):
                fire(InputEvent(id=identifier, device="keyboard", event_type="down"))
            if sig.state in (None, False):
                fire(InputEvent(id=identifier, device="keyboard", event_type="up"))

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def hook(self) -> bool:
        return self.session.start()

    def unhook(self) -> bool:
        return self.session.stop()

    def set_active(self, active: bool) -> None:
        self.session.set_active(active)

    def shutdown(self) -> None:
        self.dispatcher.unhook_all()
        self.dispatcher.worker.stop()
        self.session.shutdown()

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def normalize(self, value):
        return keymap.normalize(value)

    def compile(self, value):
        return keymap.compile(value)

    def isInput(self, value) -> bool:
        return keymap.isInput(value)

    def connections(self) -> dict[str, Connection]:
        return Connection.dict


runtime = InputRuntime()
