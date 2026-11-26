"""
Event dispatch: physical-state tracking, per-event suppression and the
user-facing hook registry.

The backend hook calls :meth:`Dispatcher.on_event` on the OS hook thread. That
method does the minimum possible work (track state, match binds, decide
suppression) and hands the bound callbacks to a small worker pool, keeping the
OS hook thread well below Windows' ``LowLevelHooksTimeout``.
"""

from __future__ import annotations

import threading
import traceback
from typing import Callable

from .events import InputEvent

__all__ = ["Dispatcher", "Worker"]


class Worker:
    """
    Callback executor used so user code never runs on the hook thread.

    One short-lived daemon thread per callback. User callbacks routinely block
    for the whole duration of a key hold (``Input.wait``, ``while
    Input.get(...)``, buffered repeats), so a fixed-size pool would make every
    other bind -- including system binds such as F2/F12 -- wait behind a held
    movement key. This mirrors the historical ``Bind`` behaviour: matching and
    suppression stay on the hook thread, execution never does.
    """

    def __init__(self, count: int | None = None) -> None:
        # ``count`` is accepted for backwards compatibility and ignored.
        self._lock = threading.RLock()
        self._idle = threading.Condition(self._lock)
        self._threads: set[threading.Thread] = set()
        self._active = 0
        self._stopped = False

    def _run(self, job: Callable[[], None]) -> None:
        try:
            job()
        except Exception:
            traceback.print_exc()
        finally:
            with self._lock:
                self._active -= 1
                self._threads.discard(threading.current_thread())
                self._idle.notify_all()

    def submit(self, job: Callable[[], None]) -> None:
        with self._lock:
            if self._stopped:
                return
            thread = threading.Thread(
                target=self._run, args=(job,), name="input-callback", daemon=True
            )
            self._threads.add(thread)
            self._active += 1

        try:
            thread.start()
        except RuntimeError:
            # Interpreter shutdown or thread exhaustion: never break the hook.
            with self._lock:
                self._active -= 1
                self._threads.discard(thread)
                self._idle.notify_all()
            traceback.print_exc()

    def drain(self, timeout: float = 2.0) -> bool:
        """Wait up to ``timeout`` seconds for running callbacks to finish."""
        with self._lock:
            return self._idle.wait_for(lambda: self._active == 0, timeout)

    def stop(self) -> None:
        with self._lock:
            self._stopped = True


class Dispatcher:
    def __init__(self, runtime) -> None:
        self.runtime = runtime
        self._hooks: dict[object, tuple[Callable, bool, str | None]] = {}
        self._lock = threading.RLock()
        self.errors: list[BaseException] = []
        self.worker = Worker()

    # ------------------------------------------------------------------
    # Input level (bind) hook
    # ------------------------------------------------------------------

    def on_event(self, event: InputEvent) -> bool:
        """
        Return ``True`` only when a blocking bind consumed the event.

        Unmatched events return ``False`` and reach the application untouched;
        there is no blanket "suppress and re-inject" fallback any more.
        """
        state = self.runtime.state

        # Track state even while suspended or for injected events.
        state.track(event)

        if event.injected:
            return False
        if event.event_type not in ("down", "up", "wheel"):
            return False

        try:
            return self.runtime.registry.dispatch(
                event,
                state,
                self.worker.submit,
                active=bool(self.runtime.session.active()),
            )
        except Exception:
            # A binding must never be able to disarm the whole system.
            self.errors.append(_current_exception())
            traceback.print_exc()
            return False

    # ------------------------------------------------------------------
    # Raw user hooks
    # ------------------------------------------------------------------

    def hook(self, callback: Callable[[InputEvent], object], device: str | None = None, suppress: bool = True):
        if not callable(callback):
            raise TypeError("callback must be callable")

        if device is None:
            wrapper = callback
        else:
            def wrapper(event: InputEvent):
                if event.device != device:
                    return False
                return callback(event)

        handle = object()
        with self._lock:
            self._hooks[handle] = (wrapper, bool(suppress), device)
        return handle

    def unhook(self, handle) -> None:
        with self._lock:
            self._hooks.pop(handle, None)

    def unhook_all(self) -> None:
        with self._lock:
            self._hooks.clear()

    def _dispatch_raw(self, event: InputEvent) -> bool:
        with self._lock:
            hooks = list(self._hooks.values())

        suppress = False
        for callback, blocking, _device in hooks:
            try:
                result = callback(event)
            except Exception:
                traceback.print_exc()
                continue
            if blocking and result is True:
                suppress = True
        return suppress

    def backend_callback(self, event: InputEvent) -> bool:
        """Entry point installed on the backend: binds first, then raw hooks."""
        suppress = self.on_event(event)
        if self._dispatch_raw(event):
            suppress = True
        return suppress


def _current_exception() -> BaseException:
    import sys

    return sys.exc_info()[1] or RuntimeError("unknown dispatch error")
