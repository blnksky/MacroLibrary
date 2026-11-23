# AHK-style identifiers shared by both backends.

KEY_ALIASES = {
    "escape": "esc",
    "return": "enter",
    "control": "ctrl",
    "lcontrol": "lctrl",
    "rcontrol": "rctrl",
    "lmenu": "lalt",
    "rmenu": "ralt",
    "prior": "pgup",
    "next": "pgdn",
    "pageup": "pgup",
    "pagedown": "pgdn",
}

MOUSE_ALIASES = {
    "left": "lbutton",
    "right": "rbutton",
    "middle": "mbutton",
    "x1": "xbutton1",
    "x2": "xbutton2",
}


def normalize(identifier):
    if not isinstance(identifier, str):
        raise TypeError("Input identifier must be a string.")

    identifier = identifier.strip().lower().replace(" ", "")

    return KEY_ALIASES.get(identifier, identifier)


def normalize_mouse(identifier):
    identifier = normalize(identifier)
    return MOUSE_ALIASES.get(identifier, identifier)
