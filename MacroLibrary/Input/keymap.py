"""
Canonical input identifiers shared by every backend.

This module is the single source of truth for:

* the public AHK-style ids (``lbutton``, ``numpad1``, ``-`` ...),
* aliases (``Escape`` -> ``esc``),
* Windows virtual-key codes and extended-key flags,
* Linux evdev key names,
* the kind of an input (key / mouse button / wheel),
* parsing of bind/send signatures.

It intentionally imports nothing from the rest of the package (and nothing
platform specific), so it can be imported on any OS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal

Kind = Literal["key", "button", "wheel", "move"]

__all__ = [
    "Kind",
    "KeySpec",
    "Signature",
    "UnknownInput",
    "IIDS",
    "KEY_IDS",
    "BUTTON_IDS",
    "WHEEL_IDS",
    "BY_VK",
    "MOUSE_VK",
    "GENERIC_MODIFIERS",
    "normalize",
    "normalize_mouse",
    "spec",
    "kind",
    "is_id",
    "expand",
    "matches",
    "compile",
    "isInput",
    "parse",
]


class UnknownInput(ValueError):
    """Raised when an identifier is not part of the canonical keymap."""


@dataclass(frozen=True, slots=True)
class KeySpec:
    id: str
    kind: Kind = "key"

    # Windows
    vk: int | None = None
    extended: bool = False

    # Linux (evdev symbolic name, resolved lazily by the Linux backend)
    linux: str | None = None

    # Text produced by this key when typed with / without shift.
    char: str | None = None
    shift_char: str | None = None

    # Wheel direction and axis.
    axis: Literal["x", "y"] = "y"
    direction: int = 0

    # Generic modifiers ("ctrl") expand to their physical sides.
    sides: tuple[str, ...] = field(default=())


# ---------------------------------------------------------------------------
# Table construction
# ---------------------------------------------------------------------------

_SPECS: dict[str, KeySpec] = {}


def _add(
    id: str,
    *,
    kind: Kind = "key",
    vk: int | None = None,
    extended: bool = False,
    linux: str | None = None,
    char: str | None = None,
    shift_char: str | None = None,
    axis: Literal["x", "y"] = "y",
    direction: int = 0,
    sides: tuple[str, ...] = (),
    aliases: Iterable[str] = (),
) -> KeySpec:
    key = KeySpec(
        id=id,
        kind=kind,
        vk=vk,
        extended=extended,
        linux=linux,
        char=char,
        shift_char=shift_char,
        axis=axis,
        direction=direction,
        sides=sides,
    )
    _SPECS[id] = key
    for alias in aliases:
        _ALIASES[alias] = id
    return key


_ALIASES: dict[str, str] = {}
_MOUSE_ALIASES: dict[str, str] = {}


# --- letters ---------------------------------------------------------------
for _c in "abcdefghijklmnopqrstuvwxyz":
    _add(
        _c,
        vk=ord(_c.upper()),
        linux=f"KEY_{_c.upper()}",
        char=_c,
        shift_char=_c.upper(),
    )

# --- digits ----------------------------------------------------------------
_DIGIT_SHIFT = ")!@#$%^&*("
for _i in range(10):
    _c = str(_i)
    _add(
        _c,
        vk=0x30 + _i,
        linux=f"KEY_{_i}",
        char=_c,
        shift_char=_DIGIT_SHIFT[_i],
    )

# --- function keys ---------------------------------------------------------
for _i in range(1, 25):
    _add(f"f{_i}", vk=0x70 + _i - 1, linux=f"KEY_F{_i}")

# --- navigation / editing --------------------------------------------------
_add("esc", vk=0x1B, linux="KEY_ESC", aliases=("escape",))
_add("tab", vk=0x09, linux="KEY_TAB", char="\t")
_add("enter", vk=0x0D, linux="KEY_ENTER", char="\n", aliases=("return",))
_add("space", vk=0x20, linux="KEY_SPACE", char=" ")
_add("backspace", vk=0x08, linux="KEY_BACKSPACE", aliases=("bs", "back"))
_add("delete", vk=0x2E, extended=True, linux="KEY_DELETE", aliases=("del",))
_add("insert", vk=0x2D, extended=True, linux="KEY_INSERT", aliases=("ins",))
_add("home", vk=0x24, extended=True, linux="KEY_HOME")
_add("end", vk=0x23, extended=True, linux="KEY_END")
_add("pgup", vk=0x21, extended=True, linux="KEY_PAGEUP", aliases=("prior", "pageup", "pgprior"))
_add("pgdn", vk=0x22, extended=True, linux="KEY_PAGEDOWN", aliases=("next", "pagedown"))
_add("up", vk=0x26, extended=True, linux="KEY_UP")
_add("down", vk=0x28, extended=True, linux="KEY_DOWN")
_add("left", vk=0x25, extended=True, linux="KEY_LEFT")
_add("right", vk=0x27, extended=True, linux="KEY_RIGHT")

# --- locks / system --------------------------------------------------------
_add("capslock", vk=0x14, linux="KEY_CAPSLOCK")
_add("numlock", vk=0x90, extended=True, linux="KEY_NUMLOCK")
_add("scrolllock", vk=0x91, linux="KEY_SCROLLLOCK")
_add("prtsc", vk=0x2C, extended=True, linux="KEY_SYSRQ", aliases=("printscreen", "sysrq"))
_add("pause", vk=0x13, linux="KEY_PAUSE")
_add("sleep", vk=0x5F, linux="KEY_SLEEP")
_add("appskey", vk=0x5D, extended=True, linux="KEY_COMPOSE", aliases=("menu", "apps"))
_add("browserback", vk=0xA6, linux="KEY_BACK")
_add("browserforward", vk=0xA7, linux="KEY_FORWARD")
_add("browserrefresh", vk=0xA8, linux="KEY_REFRESH")
_add("browserstop", vk=0xA9, linux="KEY_STOP")
_add("browsersearch", vk=0xAA, linux="KEY_SEARCH")
_add("browserfavorites", vk=0xAB, linux="KEY_BOOKMARKS")
_add("browserhome", vk=0xAC, linux="KEY_HOMEPAGE")
_add("volumemute", vk=0xAD, linux="KEY_MUTE")
_add("volumedown", vk=0xAE, linux="KEY_VOLUMEDOWN")
_add("volumeup", vk=0xAF, linux="KEY_VOLUMEUP")
_add("medianext", vk=0xB0, linux="KEY_NEXTSONG")
_add("mediaprev", vk=0xB1, linux="KEY_PREVIOUSSONG")
_add("mediastop", vk=0xB2, linux="KEY_STOPCD")
_add("mediaplay", vk=0xB3, linux="KEY_PLAYPAUSE")
_add("launchmail", vk=0xB4, linux="KEY_MAIL")
_add("launchmedia", vk=0xB5, linux="KEY_MEDIA")

# --- modifiers -------------------------------------------------------------
_add("lshift", vk=0xA0, linux="KEY_LEFTSHIFT")
_add("rshift", vk=0xA1, linux="KEY_RIGHTSHIFT")
_add("lctrl", vk=0xA2, linux="KEY_LEFTCTRL", aliases=("lcontrol",))
_add("rctrl", vk=0xA3, extended=True, linux="KEY_RIGHTCTRL", aliases=("rcontrol",))
_add("lalt", vk=0xA4, linux="KEY_LEFTALT", aliases=("lmenu",))
_add("ralt", vk=0xA5, extended=True, linux="KEY_RIGHTALT", aliases=("rmenu",))
_add("lwin", vk=0x5B, extended=True, linux="KEY_LEFTMETA")
_add("rwin", vk=0x5C, extended=True, linux="KEY_RIGHTMETA")

# Generic modifiers: injection targets the left side, matching accepts both.
GENERIC_MODIFIERS: dict[str, tuple[str, ...]] = {
    "ctrl": ("lctrl", "rctrl"),
    "shift": ("lshift", "rshift"),
    "alt": ("lalt", "ralt"),
    "win": ("lwin", "rwin"),
}
_add("ctrl", vk=0xA2, linux="KEY_LEFTCTRL", sides=GENERIC_MODIFIERS["ctrl"], aliases=("control",))
_add("shift", vk=0xA0, linux="KEY_LEFTSHIFT", sides=GENERIC_MODIFIERS["shift"])
_add("alt", vk=0xA4, linux="KEY_LEFTALT", sides=GENERIC_MODIFIERS["alt"])
_add("win", vk=0x5B, extended=True, linux="KEY_LEFTMETA", sides=GENERIC_MODIFIERS["win"], aliases=("windows", "super", "meta"))

# --- punctuation (AHK literal ids) ----------------------------------------
_add("-", vk=0xBD, linux="KEY_MINUS", char="-", shift_char="_", aliases=("minus", "oem_minus"))
_add("=", vk=0xBB, linux="KEY_EQUAL", char="=", shift_char="+", aliases=("equal", "oem_plus"))
_add("[", vk=0xDB, linux="KEY_LEFTBRACE", char="[", shift_char="{", aliases=("leftbrace", "oem_4"))
_add("]", vk=0xDD, linux="KEY_RIGHTBRACE", char="]", shift_char="}", aliases=("rightbrace", "oem_6"))
_add("\\", vk=0xDC, linux="KEY_BACKSLASH", char="\\", shift_char="|", aliases=("backslash", "oem_5"))
_add(";", vk=0xBA, linux="KEY_SEMICOLON", char=";", shift_char=":", aliases=("semicolon", "oem_1"))
_add("'", vk=0xDE, linux="KEY_APOSTROPHE", char="'", shift_char='"', aliases=("apostrophe", "quote", "oem_7"))
_add(",", vk=0xBC, linux="KEY_COMMA", char=",", shift_char="<", aliases=("comma", "oem_comma"))
_add(".", vk=0xBE, linux="KEY_DOT", char=".", shift_char=">", aliases=("dot", "period", "oem_period"))
_add("/", vk=0xBF, linux="KEY_SLASH", char="/", shift_char="?", aliases=("slash", "oem_2"))
_add("`", vk=0xC0, linux="KEY_GRAVE", char="`", shift_char="~", aliases=("grave", "oem_3"))

# --- numpad ---------------------------------------------------------------
for _i in range(10):
    _add(f"numpad{_i}", vk=0x60 + _i, linux=f"KEY_KP{_i}")
_add("numpaddot", vk=0x6E, linux="KEY_KPDOT", char=".", aliases=("numpaddecimal", "decimal"))
_add("numpaddiv", vk=0x6F, extended=True, linux="KEY_KPSLASH", char="/", aliases=("divide", "numpadslash"))
_add("numpadmult", vk=0x6A, linux="KEY_KPASTERISK", char="*", aliases=("multiply", "numpadstar"))
_add("numpadadd", vk=0x6B, linux="KEY_KPPLUS", char="+", aliases=("add",))
_add("numpadsub", vk=0x6D, linux="KEY_KPMINUS", char="-", aliases=("subtract", "minus_numpad"))
_add("numpadenter", vk=0x0D, extended=True, linux="KEY_KPENTER", char="\n")

_NUMPAD_ALIASES = {
    "numpadins": "numpad0",
    "numpadend": "numpad1",
    "numpaddown": "numpad2",
    "numpadpgdn": "numpad3",
    "numpadleft": "numpad4",
    "numpadclear": "numpad5",
    "numpadright": "numpad6",
    "numpadhome": "numpad7",
    "numpadup": "numpad8",
    "numpadpgup": "numpad9",
    "numpaddel": "numpaddot",
}
_ALIASES.update(_NUMPAD_ALIASES)

# --- additional layout-dependent keys -------------------------------------
_add("circumflex", vk=0xDE, linux="KEY_GRAVE", aliases=("deadcircumflex",))
_add("umlaut", vk=0xDE, linux="KEY_APOSTROPHE" , extended=True)
_add("less", vk=0xE2, linux="KEY_102ND", aliases=("oem_102",))
_add("´", vk=0xDD, linux="KEY_APOSTROPHE", aliases=("deadacute", "acute"))
_add("ß", vk=0xDB, linux="KEY_MINUS")

# --- mouse buttons --------------------------------------------------------
_add("lbutton", kind="button", linux="BTN_LEFT", aliases=("leftbutton",))
_add("rbutton", kind="button", linux="BTN_RIGHT", aliases=("rightbutton",))
_add("mbutton", kind="button", linux="BTN_MIDDLE", aliases=("middlebutton",))
_add("xbutton1", kind="button", linux="BTN_SIDE", aliases=("x1", "button4"))
_add("xbutton2", kind="button", linux="BTN_EXTRA", aliases=("x2", "button5"))

# --- wheel ----------------------------------------------------------------
_add("wheelup", kind="wheel", axis="y", direction=1)
_add("wheeldown", kind="wheel", axis="y", direction=-1)
_add("wheelright", kind="wheel", axis="x", direction=1)
_add("wheelleft", kind="wheel", axis="x", direction=-1)
_add("wheel", kind="wheel", axis="y", direction=0)

# Mouse-only conveniences (applied when device="mouse").
_MOUSE_ALIASES.update(
    {
        "left": "lbutton",
        "right": "rbutton",
        "middle": "mbutton",
        "x1": "xbutton1",
        "x2": "xbutton2",
        "lclick": "lbutton",
        "rclick": "rbutton",
        "mclick": "mbutton",
        "wheel": "wheelup",
    }
)

# ---------------------------------------------------------------------------
# Derived tables
# ---------------------------------------------------------------------------

IIDS: frozenset[str] = frozenset(_SPECS)
KEY_IDS: frozenset[str] = frozenset(s.id for s in _SPECS.values() if s.kind == "key")
BUTTON_IDS: frozenset[str] = frozenset(s.id for s in _SPECS.values() if s.kind == "button")
WHEEL_IDS: frozenset[str] = frozenset(s.id for s in _SPECS.values() if s.kind == "wheel")

# Virtual-key -> canonical id. ``setdefault`` keeps the first (specific) spec,
# so ``lctrl`` wins over the generic ``ctrl`` that shares VK 0xA2.
BY_VK: dict[int, str] = {}
for _spec in _SPECS.values():
    if _spec.vk is not None:
        BY_VK.setdefault(_spec.vk, _spec.id)

# Virtual-key codes used by GetAsyncKeyState for mouse buttons.
MOUSE_VK: dict[str, int] = {
    "lbutton": 0x01,
    "rbutton": 0x02,
    "mbutton": 0x04,
    "xbutton1": 0x05,
    "xbutton2": 0x06,
}

# Characters produced by ``write`` on either backend.
CHAR_MAP: dict[str, tuple[str, bool]] = {}
for _spec in _SPECS.values():
    if _spec.id.startswith("numpad"):
        continue
    if _spec.char is not None:
        CHAR_MAP.setdefault(_spec.char, (_spec.linux or "", False))
    if _spec.shift_char is not None:
        CHAR_MAP.setdefault(_spec.shift_char, (_spec.linux or "", True))


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalize(identifier: str) -> str:
    """Return the canonical lowercase id for ``identifier`` (alias aware)."""
    if not isinstance(identifier, str):
        raise TypeError("Input identifier must be a string.")
    return _ALIASES.get(identifier.strip().lower().replace(" ", ""), identifier.strip().lower())


def normalize_mouse(identifier: str) -> str:
    identifier = normalize(identifier)
    return _MOUSE_ALIASES.get(identifier, identifier)


def is_id(identifier: str) -> bool:
    return normalize(identifier) in _SPECS


def spec(identifier: str, device: str | None = None) -> KeySpec:
    """Look up a :class:`KeySpec`, applying device-specific aliases."""
    if device == "mouse":
        key = normalize_mouse(identifier)
    else:
        key = normalize(identifier)
    try:
        return _SPECS[key]
    except KeyError:
        raise UnknownInput(f"Unknown input id: {identifier!r}") from None


def kind(identifier: str) -> Kind:
    try:
        return spec(identifier).kind
    except UnknownInput:
        return "key"


def expand(identifier: str) -> tuple[str, ...]:
    """All physical ids an identifier may refer to (generic modifiers)."""
    s = spec(identifier)
    return (s.id, *s.sides)


def matches(event_id: str, bind_id: str) -> bool:
    """True when a physical ``event_id`` satisfies the logical ``bind_id``."""
    if event_id == bind_id:
        return True
    try:
        return event_id in spec(bind_id).sides
    except UnknownInput:
        return False


# ---------------------------------------------------------------------------
# Signature parsing
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Signature:
    """A parsed bind/send signature."""

    ids: tuple[str, ...] = ()
    state: bool | None = None       # None = tap, True = down, False = up
    passthrough: bool = False       # "~" prefix
    rebind: bool = False            # "#" prefix or explicit flag
    text: str | None = None         # literal text (not an input id)

    def __bool__(self) -> bool:
        return bool(self.ids) or self.text is not None


def compile(input: "str | Iterable[str]") -> tuple[str, ...]:
    """Split a signature string on commas and normalise every token."""
    if isinstance(input, str):
        tokens = [t for t in _split(input) if t]
    else:
        tokens = [str(t).strip() for t in input]
    return tuple(normalize(t) for t in tokens if t)


def _split(value: str) -> list[str]:
    stripped = value.strip()
    if stripped == "+":
        return [stripped]          # literal plus, not a separator
    return [part.strip() for part in value.replace("+", ",").split(",")]


def parse(input: "str | Iterable[str]", *, bind: bool = False, rebind: bool = False) -> Signature:
    """
    Parse ``"ctrl, a down"`` / ``("lctrl", "a")`` / ``"hello"`` into a Signature.

    ``bind=True`` additionally accepts the ``~`` (non-blocking) prefix.
    A single unknown token becomes literal text; mixing known ids with an
    unknown token raises :class:`UnknownInput`.
    """
    state: bool | None = None
    passthrough = False

    if isinstance(input, str):
        raw = input.strip()
        if not raw:
            raise ValueError("Empty input signature.")

        lowered = raw.lower()
        if lowered.endswith(" down"):
            state, raw = True, raw[: -len(" down")]
        elif lowered.endswith(" up"):
            state, raw = False, raw[: -len(" up")]

        raw = raw.strip()
        if bind and raw.startswith("~"):
            passthrough, raw = True, raw[1:].strip()
        if raw.startswith("#"):
            rebind, raw = True, raw[1:].strip()

        tokens = [t for t in _split(raw) if t]
        if not tokens:
            raise ValueError(f"Empty input signature: {input!r}")
    else:
        tokens = [str(t).strip() for t in input if str(t).strip()]
        if not tokens:
            raise ValueError("Empty input signature.")

    ids: list[str] = []
    unknown: list[str] = []
    for token in tokens:
        token_lower = token.lower()
        if token_lower.endswith(" down"):
            state, token = True, token[:-5]
        elif token_lower.endswith(" up"):
            state, token = False, token[:-3]
        canonical = normalize(token)
        if canonical in _SPECS:
            if canonical not in ids:
                ids.append(canonical)
        else:
            unknown.append(token)

    if unknown:
        if len(tokens) == 1 and not ids:
            return Signature(ids=(), state=state, passthrough=passthrough, rebind=rebind, text=tokens[0])
        raise UnknownInput(f"Unknown input id(s): {', '.join(unknown)}")

    return Signature(ids=tuple(ids), state=state, passthrough=passthrough, rebind=rebind)


def isInput(input: "str | Iterable[str]") -> bool:
    try:
        sig = parse(input)
    except (UnknownInput, ValueError):
        return False
    return bool(sig.ids) and sig.text is None
