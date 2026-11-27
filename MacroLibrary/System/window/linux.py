"""
Active-window title on Linux (X11 / XWayland), via ``python-xlib``.

The window manager publishes the focused window in ``_NET_ACTIVE_WINDOW`` on
the root window; its title is ``_NET_WM_NAME`` (UTF-8) or the older
``WM_NAME``. Native Wayland windows do not participate in this protocol, so
the lookup returns ``None`` there. ``Sys.toggle`` treats a ``None`` title as
"do not apply the appId gate".
"""

from __future__ import annotations

__all__ = ["getActiveWindowTitle"]


def _decode(value) -> str | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, (bytes, bytearray)):
        try:
            value = bytes(value)
        except Exception:
            return None
    raw = bytes(value)
    if not raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", "replace")


def getActiveWindowTitle() -> str | None:
    """Return the title of the focused X11 window, or ``None``."""
    try:
        from Xlib import X, display
        from Xlib.error import XError
    except ImportError:
        return None

    try:
        conn = display.Display()
    except Exception:
        return None

    try:
        root = conn.screen().root
        active = root.get_full_property(
            conn.intern_atom("_NET_ACTIVE_WINDOW"), X.AnyPropertyType
        )
        if active is None or not active.value:
            return None

        window = conn.create_resource_object("window", int(active.value[0]))
        if window is None:
            return None

        candidates = (
            ("_NET_WM_NAME", conn.intern_atom("UTF8_STRING")),
            ("WM_NAME", X.AnyPropertyType),
        )
        for name, req_type in candidates:
            try:
                prop = window.get_full_property(conn.intern_atom(name), req_type)
            except XError:
                continue
            if prop is None or prop.value is None:
                continue
            title = _decode(prop.value)
            if title:
                return title
        return None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass
