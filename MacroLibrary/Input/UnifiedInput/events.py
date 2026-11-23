from dataclasses import dataclass
from typing import Optional , Literal


@dataclass
class InputEvent:
    id: str
    device: str
    event_type: str | Literal["down"] | Literal["up"]

    scan_code: Optional[int] = None
    vk_code: Optional[int] = None

    x: Optional[int] = None
    y: Optional[int] = None

    delta: Optional[int] = None

    injected: bool = False
    device_id: Optional[str] = None
