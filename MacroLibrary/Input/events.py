"""
The single event type exchanged by backends, the dispatcher and user hooks.

Both the Windows and the Linux backend produce exactly this object, so user
code never has to care which platform it runs on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from . import keymap

__all__ = ["InputEvent"]

Device = Literal["keyboard", "mouse"]
EventType = Literal["down", "up", "move", "wheel"]
Kind = Literal["key", "button", "wheel", "move"]


@dataclass(slots=True)
class InputEvent:
    id: str
    device: Device = "keyboard"
    event_type: EventType = "down"
    kind: Kind | None = None

    # Keyboard details
    scan_code: int | None = None
    vk_code: int | None = None

    # Pointer details
    x: int | None = None
    y: int | None = None
    dx: int | None = None
    dy: int | None = None
    delta: int | None = None

    injected: bool = False
    device_id: str | None = None

    def __post_init__(self) -> None:
        if self.kind is None:
            if self.event_type == "move":
                self.kind = "move"
            elif self.event_type == "wheel":
                self.kind = "wheel"
            else:
                self.kind = keymap.kind(self.id) if keymap.is_id(self.id) else "key"

    @property
    def is_down(self) -> bool:
        return self.event_type == "down"

    @property
    def is_up(self) -> bool:
        return self.event_type == "up"
