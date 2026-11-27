"""
Active-window change notifications.

The watcher polls :func:`getActiveWindowTitle` on a daemon thread and fires
:data:`changed` whenever the title differs from the previously observed one.
Watching is opt-in: call :func:`watch` to start and :func:`unwatch` to stop.
"""

from __future__ import annotations

import threading
import traceback

from ...Structures import Event
from . import _platform

__all__ = ["changed", "title", "watching", "watch", "unwatch"]

#: Fired with the new active-window title whenever it changes. ``None`` means
#: no title could be read, for example a native Wayland window.
changed: Event[[str | None]] = Event()

_lock = threading.RLock()
_thread: threading.Thread | None = None
_stop: threading.Event | None = None
_title: str | None = None


def title() -> str | None:
    """Return the most recently observed active-window title."""
    with _lock:
        return _title


def watching() -> bool:
    """Return whether the watcher thread is running."""
    with _lock:
        return _thread is not None and _thread.is_alive()


def watch(interval: int = 250) -> bool:
    """
    Start watching for active-window changes.

    ``interval`` is the poll interval in milliseconds. Returns ``True`` when
    the watcher was started, or ``False`` when it was already running.
    """
    global _thread, _stop, _title

    with _lock:
        if _thread is not None and _thread.is_alive():
            return False

        stop = threading.Event()
        _stop = stop
        try:
            _title = _platform.getActiveWindowTitle()
        except Exception:
            _title = None
        _thread = threading.Thread(
            target=_run,
            args=(stop, max(1, int(interval))),
            name="MacroLibrary-window-watch",
            daemon=True,
        )
        _thread.start()
        return True


def unwatch(timeout: int | None = None) -> bool:
    """
    Stop watching. Returns ``True`` if a watcher was running.

    ``timeout`` is the join timeout in milliseconds; ``None`` waits for the
    polling thread to finish. Calling this from inside a callback is safe.
    """
    global _thread, _stop

    with _lock:
        thread = _thread
        stop = _stop
        if thread is None:
            return False
        _thread = None
        _stop = None

    if stop is not None:
        stop.set()
    if thread is not threading.current_thread():
        thread.join(None if timeout is None else max(0, timeout) / 1000)
    return True


def _run(stop: threading.Event, interval: int) -> None:
    global _title

    # ``watch`` seeds ``_title`` synchronously, so the first poll can already
    # detect a focus change that happened between start-up and this thread.
    known = True

    while not stop.is_set():
        try:
            value = _platform.getActiveWindowTitle()
        except Exception:
            value = None

        with _lock:
            changed_now = known and value != _title
            known = True
            _title = value

        if changed_now:
            try:
                changed(value)
            except Exception:
                traceback.print_exc()

        stop.wait(interval / 1000)
