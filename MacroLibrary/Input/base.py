"""
Public high level Input facade.

All implementation lives in the sibling modules; this file only re-exports the
supported surface (plus a few compatibility aliases used by ``System``).
"""

from .common import *          # noqa: F401,F403 - legacy star import surface
from . import backend as uin
from .backend import InputAPI, InputHandler, Backend

from .binding import Bind, Connection, InputConnection, Registry
from .dispatch import Dispatcher, Worker
from .events import InputEvent
from .keymap import (
    IIDS,
    KEY_IDS,
    BUTTON_IDS,
    WHEEL_IDS,
    Signature,
    UnknownInput,
    compile,
    expand,
    isInput,
    kind,
    normalize,
    parse,
    spec,
)
from .runtime import InputRuntime, runtime
from .session import Session
from .state import InputState

# ---------------------------------------------------------------------------
# Runtime singletons
# ---------------------------------------------------------------------------

backend = uin.backend
api = uin.api

enabled = runtime.enabled              # State[bool]: active / suspended
state = runtime.state
registry = runtime.registry
dispatcher = runtime.dispatcher
session = runtime.session

send = runtime.send                    # Event
down = runtime.down
up = runtime.up

hotkeyBuffer = runtime.hotkeyBuffer
bufferDuration = runtime.bufferDuration
bufferInterval = runtime.bufferInterval

# Live compatibility views.
inputStates = runtime.state._counts
inputQueue = runtime.state._queue
stateTS = runtime.state._timestamps
rebinds = runtime.remaps

# ---------------------------------------------------------------------------
# Low level (merged keyboard + mouse) passthrough
# ---------------------------------------------------------------------------

press = uin.press
release = uin.release
hold = uin.hold
is_pressed = uin.is_pressed
write = uin.write

move = uin.move
move_to = uin.move_to
wheel = uin.wheel
click = uin.click
get_position = uin.get_position
release_all = uin.release_all

keyboard = uin.keyboard
mouse = uin.mouse


# ---------------------------------------------------------------------------
# High level functions
# ---------------------------------------------------------------------------

def get(input) -> bool:
    """Return the physical state of an input signature."""
    return runtime.get(input)


def last(id: InputId, state: bool | None = None):
    """Last state-change timestamp (or ``(state, timestamp)``)."""
    return runtime.last(id, state)


def wait(id: InputId, timeout: int | None = None, pressed: bool | None = None) -> bool:
    """Block until ``id`` reaches ``pressed`` (default: the opposite state)."""
    return runtime.wait(id, timeout, pressed)


def toggle(id: InputId, timeout: int = 0) -> None:
    """Send ``id`` in its stated state, then resolve it against physical state."""
    runtime.toggle(id, timeout)


def trigger(id: InputId, delay: int = 0) -> None:
    """Emit the opposite state before the actual signal (legacy helper)."""
    runtime.trigger(id, delay)


def resolve(input) -> None:
    """Synchronise virtual output state with the physical state of ``input``."""
    runtime.resolve(input)


def rebind(input, output) -> Bind:
    """Create a real down/up remap from ``input`` to ``output``."""
    return runtime.rebind(input, output)


def buffer(inp, duration: int | None = None, interval: int | None = None) -> Bind:
    """Repeat ``inp`` while it is held (optionally for ``duration`` after release)."""
    return runtime.bind_buffer(inp, duration, interval)


def simulate(id: InputId) -> None:
    """Feed synthetic events through the binding layer (no OS injection)."""
    runtime.simulate(id)


def bind(input, call, *, block: bool | None = None, enabled: bool = True, always: bool = False) -> Bind:
    """Explicit ``Bind`` constructor bound to this runtime."""
    return runtime.bind(input, call, block=block, enabled=enabled, always=always)


# ---------------------------------------------------------------------------
# Hook / suspend
# ---------------------------------------------------------------------------

def hook() -> bool:
    """Install the global hook (binds are active by default)."""
    return runtime.hook()


def unhook() -> bool:
    """Remove the global hook."""
    return runtime.unhook()


def set_active(active: bool) -> None:
    runtime.set_active(active)


def shutdown() -> None:
    runtime.shutdown()


__all__ = [
    # backend package / instances
    "uin", "backend", "api", "Backend", "InputAPI", "InputHandler",

    # keymap / parsing
    "IIDS", "KEY_IDS", "BUTTON_IDS", "WHEEL_IDS",
    "Signature", "UnknownInput",
    "normalize", "compile", "isInput", "parse", "spec", "kind", "expand",

    # state / session
    "enabled", "state", "registry", "dispatcher", "session",
    "InputState", "InputEvent", "Session", "Dispatcher", "Worker", "InputRuntime",

    # events / helpers
    "send", "down", "up",
    "get", "last", "wait", "toggle", "trigger", "resolve",
    "hotkeyBuffer", "bufferDuration", "bufferInterval",

    # low level
    "press", "release", "hold", "is_pressed", "write",
    "move", "move_to", "wheel", "click", "get_position", "release_all",
    "keyboard", "mouse",

    # binding
    "Bind", "Connection", "InputConnection", "Registry",
    "bind", "rebind", "buffer", "simulate",

    # lifecycle
    "hook", "unhook", "set_active", "shutdown",

    # compatibility
    "runtime", "inputStates", "inputQueue", "stateTS", "rebinds",
]
