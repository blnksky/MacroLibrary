"""
Bindings and the binding registry.

A ``Bind`` is a declarative rule: "when this signature fires, run this
callback". Binds are disabled by default and do not own any global state. The
``Registry`` decides, per event, which binds fire and whether the event is
consumed. This replaces ``Bind``/``InputConnection``/``block`` bookkeeping from
the old ``base.py``.
"""

from __future__ import annotations

import threading
import traceback
from typing import Any, Callable, Iterable

from . import keymap
from .events import InputEvent
from .state import InputState
from ..common import matchParams

__all__ = ["Bind", "Registry", "Connection", "InputConnection"]


class Bind:
    """A match rule plus a callback."""

    #: Every Bind ever constructed (kept for backwards compatibility).
    set: "set[Bind]" = set()
    #: Registry used when ``registry=`` is not passed explicitly.
    registry: "Registry | None" = None

    def __init__(
        self,
        input,
        call: Callable[[str], Any],
        *,
        block: bool | None = None,
        enabled: bool = True,
        always: bool = False,
        registry: "Registry | None" = None,
    ) -> None:
        sig = keymap.parse(input, bind=True)
        if sig.text is not None or not sig.ids:
            raise ValueError("A Bind requires one or more input ids, not literal text.")

        self.signature = sig
        self.input: tuple[str, ...] = sig.ids
        self.state: bool | None = sig.state
        self.block: bool = (not sig.passthrough) if block is None else bool(block)
        self.enabled: bool = enabled
        self.always: bool = bool(always)   # keeps firing while the session is suspended
        self.eventState: bool = sig.state is not False

        self.call: Callable[[str], Any] = matchParams(lambda id: None, call)
        self.name: str = getattr(call, "__name__", "<bind>")

        self._lock = threading.RLock()
        self._active = False
        self._down = False

        Bind.set.add(self)
        self._registry = registry if registry is not None else Bind.registry
        if self._registry is not None:
            self._registry.register(self)
        else:
            for i in self.input:
                Connection.get(i).add(self)

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def matches(self, event: InputEvent, state: InputState) -> bool:
        if not self.enabled or event.event_type not in ("down", "up", "wheel"):
            return False

        touches = any(keymap.matches(event.id, i) for i in self.input)
        if not touches:
            return False

        pressing = event.event_type in ("down", "wheel")

        # A release always clears the "already fired for this press" flag.
        if not pressing:
            self._down = False
            if self.state is not False:
                return False
        else:
            if self.state is False:
                return False

        # Every *other* key of the chord must currently be down.
        for i in self.input:
            if keymap.matches(event.id, i):
                continue
            if not state.pressed(i):
                return False

        if event.event_type == "down":
            if self.state is None and self._down:
                return False          # auto-repeat while held
            self._down = True

        return True

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def fire(self, event: InputEvent, submit: Callable[[Callable[[], None]], None] | None = None) -> None:
        with self._lock:
            if self._active:
                return
            self._active = True

        def run() -> None:
            try:
                self.call(event.id)
            except Exception:
                traceback.print_exc()
            finally:
                with self._lock:
                    self._active = False

        if submit is None:
            run()
        else:
            submit(run)

    def __call__(self, event_id: str) -> bool:
        """Schedule the callback directly (historical `Bind(id)` behaviour)."""
        self.fire(InputEvent(id=event_id), None)
        return True

    def toggle(self, enabled: bool) -> "Bind":
        self.enabled = bool(enabled)
        pair = getattr(self, "pair", None)
        if pair is not None:
            pair.enabled = self.enabled
        return self

    def __repr__(self) -> str:
        return f"<Bind {self.input!r} block={self.block} enabled={self.enabled}>"


class Registry:
    """Ordered collection of binds + per-event dispatch."""

    def __init__(self) -> None:
        self._binds: list[Bind] = []
        self._lock = threading.RLock()
        self._consumed_down: set[str] = set()
        self.errors: list[BaseException] = []

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    def register(self, bind: Bind) -> Bind:
        with self._lock:
            if bind not in self._binds:
                self._binds.append(bind)
        for i in bind.input:
            Connection.get(i).add(bind)
        return bind

    def unregister(self, bind: Bind) -> None:
        with self._lock:
            if bind in self._binds:
                self._binds.remove(bind)
        Bind.set.discard(bind)
        for i in bind.input:
            conn = Connection.dict.get(i)
            if conn is not None:
                conn.discard(bind)

    def clear(self) -> None:
        with self._lock:
            self._binds.clear()
            self._consumed_down.clear()
        Bind.set.clear()
        Connection.dict.clear()

    def binds(self) -> tuple[Bind, ...]:
        with self._lock:
            return tuple(self._binds)

    def toggle(self, enabled: bool) -> None:
        for bind in self.binds():
            bind.toggle(enabled)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(
        self,
        event: InputEvent,
        state: InputState,
        submit: Callable[[Callable[[], None]], None] | None = None,
        active: bool = True,
    ) -> bool:
        """
        Fire matching binds and report whether the event must be suppressed.

        Blocking binds (the default) consume the event; ``~`` binds run without
        consuming. An up event is also consumed when its matching down was
        consumed, so a remap never leaks a stray release.
        """
        if event.event_type not in ("down", "up", "wheel"):
            return False

        candidates = [
            b for b in self.binds()
            if (active or b.always) and b.matches(event, state)
        ]
        # Chords first, blocking before passthrough.
        candidates.sort(key=lambda b: (not b.block, -len(b.input)))

        consumed = False
        for bind in candidates:
            bind.fire(event, submit)
            if bind.block:
                consumed = True

        if event.event_type == "wheel":
            return consumed

        if event.event_type == "down":
            if consumed:
                self._consumed_down.add(event.id)
            return consumed

        if event.id in self._consumed_down:
            self._consumed_down.discard(event.id)
            return True
        return consumed


class Connection:
    """
    Compatibility view over the binds of a single input id.

    The old implementation used it as the enable/suppression owner. In the new
    model enablement lives on ``Bind`` and suppression is decided per event, so
    this is only a discovery aid (``Input.Connection.get("e").binds``).
    """

    dict: "dict[str, Connection]" = {}

    def __init__(self, id: str) -> None:
        self.id = keymap.normalize(id)
        self.binds: set[Bind] = set()
        self.dict[self.id] = self

    @classmethod
    def get(cls, id: str) -> "Connection":
        key = keymap.normalize(id)
        conn = cls.dict.get(key)
        return conn if conn is not None else cls(key)

    def add(self, bind: Bind) -> None:
        self.binds.add(bind)

    def discard(self, bind: Bind) -> None:
        self.binds.discard(bind)

    @property
    def enabled(self) -> bool:
        return any(b.enabled for b in self.binds)

    def toggle(self, enabled: bool | None = None) -> None:
        if enabled is None:
            enabled = not self.enabled
        for bind in self.binds:
            bind.toggle(enabled)

    def __iter__(self) -> Iterable[Bind]:
        return iter(self.binds)

    def __len__(self) -> int:
        return len(self.binds)

    def __repr__(self) -> str:
        return f"<Connection {self.id!r} binds={len(self.binds)}>"


InputConnection = Connection
