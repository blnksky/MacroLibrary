# MacroLibrary

A small Python framework for building desktop input macros: global keyboard and
mouse hooks, bindings, remaps, buffered repeats, and a `Sys` lifecycle with
enable/disable hotkeys and foreground-app gating.

The `Input` layer has both a Windows and a Linux backend. Windows uses
low-level hooks and scan-code `SendInput`; Linux uses `evdev` + `uinput`.
`Sys` captures the foreground window with `pygetwindow` on Windows and
`python-xlib` on Linux (X11 / XWayland).

---

## Contents

1. [Requirements and install](#requirements-and-install)
2. [Quick start](#quick-start)
3. [How the package is organised](#how-the-package-is-organised)
4. [Configuration](#configuration)
5. [Lifecycle and hotkeys](#lifecycle-and-hotkeys)
6. [Window tracking](#window-tracking)
7. [Bindings](#bindings)
8. [Rebinds and buffered input](#rebinds-and-buffered-input)
9. [Sending input](#sending-input)
10. [State and Event helpers](#state-and-event-helpers)
11. [A complete build script](#a-complete-build-script)
12. [Updating older scripts](#updating-older-scripts)
13. [Troubleshooting](#troubleshooting)
14. [Platform notes](#platform-notes)

---

## Requirements and install

- Python **3.12+** (the package uses PEP 695 `type` aliases).
- Windows, or Linux with X11 / XWayland.
- Platform dependencies are selected automatically: `pygetwindow` on Windows,
  `python-xlib` and `evdev` on Linux.

Install from a checkout:

```powershell
pip install -e .
```

or directly from Git:

```powershell
pip install "git+https://github.com/blnksky/MacroLibrary.git"
```

`Sys.toggle()` reads the foreground window title, used by the `appId` gate,
through `pygetwindow` on Windows and `python-xlib` on Linux.

Minimal import surface:

```python
from MacroLibrary import *   # Sys, State, Event, sleep, delay, now, ...
import MacroLibrary.Input as Input
```

`MacroLibrary.Input` is also re-exported through the star import, so
`Input.send(...)` works after `from MacroLibrary import *`.

---

## Quick start

```python
from MacroLibrary import *

# 1. Describe this script.
Sys.config.update({
    "appId": "Roblox",
    "binds": {"default": True},
    "rebinds": {("~lalt", "lshift")},
})

# 2. Register bindings. The callback receives the physical event id.
def dash(event_id):
    Input.send("q")

Sys.bind("lshift", dash, category="default")

# 3. Start the system.
if __name__ == "__main__":
    Sys.load()
```

Run the script, focus the target window, and press **F1**. The console prints
the active window and `-- system enabled --`. Press `lshift` and the script
taps `q`.

With `Sys`, the system always starts **disabled**. Nobody receives macro
output until you enable it.

These docs describe the current checkout, where configuration lives on
`Sys.config` and binds are registered with `Sys.bind`. Released builds still
use the older module-level `config` and `Sys.bindData`; see
[Updating older scripts](#updating-older-scripts).

---

## How the package is organised

| Part | What it does |
|---|---|
| `MacroLibrary.Input` | OS hooks, key names, physical state, sending, binds, rebinds, buffering. |
| `MacroLibrary.System` | `Sys`: config, lifecycle, enable/disable, foreground-app gate, system hotkeys. `System.window` reads the foreground title and watches for changes. |
| `MacroLibrary.Structures` | `State` and `Event`, small observable primitives used by scripts. |
| `MacroLibrary.common` | `sleep`, `delay`, `now`, `path`, `matchParams`, `updateDict`. |

You can use `Input` on its own. `Sys` is a convenience layer around it for
game-style scripts: config, one startup call, one enable hotkey, one exit
hotkey.

---

## Configuration

### `Sys.config`

`Sys.config` is a nested dictionary with these keys:

```python
{
    "build":   "",      # optional second JSON file to merge
    "appId":   "",      # foreground window title that may enable the system
    "binds":   {},      # category name -> True/False
    "inputs":  {},      # your own logical-name -> key map
    "rebinds": set(),   # {(input, output), ...}
}
```

Update it with `Sys.config.update({...})`. Nested dictionaries are merged,
sets are unioned, and other values are replaced:

```python
Sys.config.update({
    "appId": "Roblox",
    "binds": {"default": True, "combat": False},
    "inputs": {
        "block": "f",
        "dash": "q",
    },
    "rebinds": {
        ("~lalt", "lshift"),
        ("g", "v"),
    },
})
```

`binds` is the switchboard for **categories**. A bind registered with
category `""` (the default) is always loaded. A bind registered with any other
category is loaded only when `Sys.config["binds"][category]` is truthy:

```python
Sys.bind("q", on_aux)                      # always loaded
Sys.bind("f", on_block, category="combat") # needs binds["combat"] == True
```

`inputs` is not interpreted by the library. It is a convenient place to keep
the logical in-game key map that your own script reads, for example
`inputs["block"]`.

`rebinds` is applied by `Sys.load()` before any bindings are created.

### Loading a JSON file

`Sys.config` can also be filled from JSON:

```python
Sys.config["build"] = "overlay.json"   # optional, merged on top
Sys.config.load("config.json")
```

```json
{
    "appId": "Roblox",
    "inputs": {"block": "f"},
    "binds": {"default": true},
    "rebinds": [["~lalt", "lshift"], ["g", "v"]]
}
```

`rebinds` may be a list of pairs or an object of `input: output`; both are
normalised to a set of pairs. JSON cannot hold callbacks, so binds still need
`Sys.bind(...)` in Python.

### Foreground-app gate (`appId`)

`Sys` keeps two states:

- `Sys.state` is the **intended** state. F1, F2, and `Sys.toggle()` change it.
  It is the same object as `Input.enabled`.
- `Sys.active` is the **real** state:
  `Sys.state and the foreground title matches Sys.appId`. Normal binds are
  enabled only while `Sys.active` is true.

The match is exact and case-sensitive against the full window title. If the
focused window does not match, the intended state can still be on while the
system stays inactive:

```text
active window: Rogue Lineage Battlegrounds | Play on Roblox - Chrome
-- system disabled --
-- intended enabled , waiting for window --
```

Arm the system with F1 even while the wrong window is focused, then switch to
the target: `Sys.active` turns on automatically. Switching away turns it off
without changing `Sys.state`, so switching back re-enables only if you left it
armed. If the system was off before you left, it stays off when you return.

`appId` comes from `Sys.config["appId"]` when non-empty. An empty value leaves
`Sys.appId` as `None`, which disables the gate:

```python
Sys.appId = None          # accept any foreground window (use None, not "")
Sys.appId = "Roblox"      # exact title only
```

On Linux the title is read from X11. Native Wayland windows may not expose a
title, in which case the lookup returns `None` and the gate is skipped.

Only `Sys` binds follow `Sys.active`. Binds created with `Input.bind` directly
are not gated.

---

## Lifecycle and hotkeys

### `Sys.load()`

```python
Sys.load()
```

This does, in order:

1. starts a non-daemon lifeline thread so the process stays alive after the
   script ends;
2. copies `Sys.config["appId"]` into `Sys.appId` (if non-empty);
3. applies `Sys.config["rebinds"]`;
4. creates binds for every enabled category;
5. installs the global keyboard/mouse hook;
6. starts the active-window watcher;
7. marks the system as loaded and sets the intended state off, so all normal
   binds start disabled.

Because of the lifeline thread, `if __name__ == "__main__": Sys.load()` is
enough to keep the script running.

### System hotkeys

These are always available, even while the system is disabled:

| Key | Action |
|---|---|
| **F1** | Toggle the intended state on/off; `Sys.active` follows the window gate. |
| **F2** | Force the intended state off (and therefore `Sys.active` off). |
| **F12** | Exit: disable, stop the watcher, remove the hook, end the lifeline thread. |

`Sys.toggle(state=None)` changes the intended state from code:

```python
Sys.toggle()        # flip the intended state
Sys.toggle(True)    # arm it; Sys.active follows the window
Sys.toggle(False)   # force it off
```

Printing is intentional. Use the console lines to see what `Sys` decided and
which foreground title it saw.

### `Sys.exit()`

```python
Sys.exit()
```

Stops the system and the backend. F12 calls this for you. Treat it as the end
of the process: it also stops the callback worker, so do not call `Sys.load()`
again in the same interpreter.

### Using `Input` without `Sys`

```python
import MacroLibrary.Input as Input

Input.bind("f", lambda event_id: Input.send("lbutton"))
Input.hook()

# later
Input.set_active(False)   # soft suspend: dispatch stops, hook stays installed
Input.set_active(True)
Input.unhook()            # remove the hook
Input.shutdown()          # unhook + release held keys + stop backend
```

`Input.hook()` returns `True` when it installed the hook and `False` when it
was already installed. `Input.shutdown()` is terminal for the callback worker
as well; use `Input.unhook()` to remove only the hook, or
`Input.set_active(False)` to pause dispatch.

`Input.set_active(False)` is a **soft suspend**: the registry stops matching
events, but the hook remains installed and bind enable flags are untouched.
`Sys.toggle()` is the hard switch: it also toggles each normal bind's
`enabled` flag.

---

## Window tracking

`MacroLibrary.System.window` exposes the foreground window. `Sys` uses the same
watcher to keep `Sys.active` in sync with the focused window.

```python
from MacroLibrary.System import window

window.getActiveWindowTitle()   # read once; None when unavailable

def on_window(title):
    print("focused:", title)

window.changed.connect(on_window)
window.watch()                  # start polling, default 250 ms

# later
window.title()                  # last title seen by the watcher
window.watching()               # True while the watcher thread runs
window.unwatch()                # stop polling
```

- `window.changed` is an `Event` that receives the new title. Use `sync` for
  ordered, inline callbacks or `connect` for parallel callbacks, like any
  other event. `sync` callbacks run on the watcher thread and delay the next
  poll, so keep them short; use `connect` for slow work.
- `window.watch(interval=250)` starts a daemon polling thread. `interval` is
  in milliseconds. It returns `False` if the watcher was already running.
- The watcher does **not** fire for the title it sees when started; it fires on
  later changes. `window.title()` already has that first value (or `None`).
- Changes are detected by comparing titles, so two windows with identical
  titles are treated as unchanged. `None` is passed when no title can be read,
  including native Wayland windows.
- `window.unwatch()` stops the thread. Calling it from inside a `changed`
  callback is safe.
- `Sys.load()` starts this watcher and `Sys.exit()` stops it if `Sys` started
  it. `window.changed` refreshes `Sys.active`, so focus changes update the real
  state automatically. Calling `window.unwatch()` yourself also stops those
  automatic updates.

---

## Bindings

### Registering a bind

```python
Sys.bind(input="f", call=on_block)                 # category ""
Sys.bind("f", on_block, category="combat")         # category "combat"
```

`call` may accept either no arguments or one argument. With one argument it
receives the physical event id that completed the bind:

```python
def on_block(event_id):
    Input.send("f", True)
    Input.wait(event_id)       # wait for the physical key release
    Input.send("f", False)
```

Binds can also be created directly, with explicit flags:

```python
Input.bind("f", on_block, block=True, enabled=True, always=False)
```

- `block=True` consumes the physical event (default; `~` sets it to false).
- `enabled=False` creates the bind switched off.
- `always=True` keeps the bind active while the session is suspended. `Sys`
  uses this for F1/F2/F12.

Calling `Sys.bind` **after** `Sys.load()` creates the bind immediately and
sets its enabled flag to the current system state.

### Input names and signatures

Key names are lowercase, case-insensitive, and alias-aware.

```python
"a"                  # letter
"1"                  # digit
"f1" ... "f24"       # function keys
"lshift" "rshift" "lctrl" "rctrl" "lalt" "ralt" "lwin" "rwin"
"shift" "ctrl" "alt" "win"          # generic: targets the left key
"space" "enter" "esc" "tab" "backspace" "delete" "insert"
"home" "end" "pgup" "pgdn" "up" "down" "left" "right"
"capslock" "numlock" "scrolllock" "prtsc" "pause"
"numpad0" ... "numpad9" "numpadadd" "numpadsub" "numpadmult" "numpaddiv"
"lbutton" "rbutton" "mbutton" "xbutton1" "xbutton2"
"wheelup" "wheeldown" "wheelleft" "wheelright"
"ß" "´" "less" "umlaut" "circumflex"
```

A signature can be a string or a tuple/list of ids:

```python
"lctrl, a"          # chord, comma separated
"lctrl+a"           # same chord, plus separated
("lctrl", "a")      # same chord, tuple form
"q down"            # press event only
"q up"              # release event only
"~lalt"             # non-blocking bind prefix
"#g"                # look up the rebind map when sending
```

`~` is only meaningful in bind signatures. It means "let the physical event
through to the app as well". Without `~`, a bind blocks the key by default.

A single token that is not a known key name becomes **literal text** (for
example `"hello"`), and `Input.send` types it with Unicode events. A mix of
known keys and unknown tokens raises `UnknownInput`. Literal text is an
output-only form: `Bind` and `Sys.bind` require known key ids.

### Blocking, passthrough, and chords

- A blocking bind consumes the physical event and its OS auto-repeat for the
  whole hold, so the app never sees a stray half-press.
- A `~` bind (or `block=False`) runs without consuming. The app still gets
  the key.
- Matching blocking binds are ordered longest-first, so a blocking chord wins
  over a shorter blocking bind.
- Matching non-blocking (`~`) binds always fire, whether or not a blocking
  bind also matched.
- Once a blocking bind fires for an event, shorter blocking combinations are
  skipped.
- A newer blocking bind replaces an older blocking bind with the same input
  and the same event state. A non-blocking bind never replaces anything and
  is never replaced.
- Rebinds create an explicit down bind and an explicit up bind, so they do
  not collide with a `~` passthrough bind on the same key.

### Callbacks and threading

The OS hook thread only tracks physical state, matches binds, and decides
whether to consume the event. Your callback runs on its own daemon thread, so
it is safe to block inside it:

```python
def hold_to_attack(event_id):
    Input.send("lbutton", True)
    Input.wait(event_id)        # blocks until the physical key is released
    Input.send("lbutton", False)
```

Exceptions inside callbacks are printed and do not kill the hook. Do not
assume callbacks run in order or on a single thread.

### Physical state

The library tracks physical (non-injected) presses only. State is populated by
the installed hook, so call `Input.hook()` (or `Sys.load()`) before relying on
it.

```python
Input.get("w")                 # physical state, chord aware
Input.get("lctrl, w")
Input.is_pressed("w")          # virtual held state + OS physical state
Input.wait("w")                # wait for the opposite of the current state
Input.wait("w", 2000)          # milliseconds
Input.wait("w", pressed=True)  # wait for it to go down
Input.last("w")                # (state, timestamp_ms)
Input.last("w", True)          # timestamp of the last down
```

Because injected output is ignored by physical state, a macro's own `send`
calls cannot re-trigger its binds.

---

## Rebinds and buffered input

### `Sys.rebind` / `Input.rebind`

```python
Sys.rebind("lalt", "lshift")        # lalt mirrors lshift down/up
Sys.rebind("~lalt", "lshift")       # same, original lalt still passes through
Sys.rebind("y", "6")                # one key to another
Sys.rebind("x", "hello")            # literal text: typed once per press
```

Behaviour:

- For key/chord outputs, the down state and up state are mirrored for the
  whole hold.
- If the output is literal text, or the input signature names an explicit
  state (`"x down"`), the output is tapped once.
- `~` on the input keeps the original key working. Without `~`, the input is
  consumed.
- The rebind is implemented as a normal blocking down/up pair, so it can be
  toggled and replaced like any other bind. `Sys.rebind` adds it to
  `Sys.binds` and toggles it with the system.

The map is also stored in `Input.rebinds`. Sending a signature with a `#`
prefix resolves it:

```python
Input.send("#g")       # send whatever "g" is rebound to
```

### `Sys.buffer` / `Input.buffer`

Repeat an input while it is held:

```python
Sys.buffer("w")                       # defaults: 25 ms interval, 150 ms overshoot
Sys.buffer("w", duration=300, interval=50)
```

The bind is a passthrough (`~`) bind, so the original key still reaches the
app. The repeat starts on the next press, continues while held, and keeps
going for `duration` milliseconds after release. With `duration=0` it stops at
the next repeat tick after the key is released.

The defaults live in `Input.bufferDuration` (150 ms) and
`Input.bufferInterval` (25 ms).

---

## Sending input

### `Input.send`

```python
Input.send("q")               # tap
Input.send("q", True)         # press and hold
Input.send("q", False)        # release
Input.send("lctrl, a")        # tap a chord
Input.send("q down")          # press, from the signature
Input.send("hello")           # literal text (Unicode)
```

- `state=None` taps: press then release. Chord ids are pressed in order and
  released in reverse.
- `state=True` presses and leaves held. `state=False` releases.
- A single unknown token (for example `"hello"`) is typed with Unicode
  `KEYEVENTF_UNICODE` events. Use real key ids for games or apps that ignore
  Unicode injection.
- `Input.send` is an `Event`, so you can observe every send:

```python
Input.send.connect(lambda input, state=None: print("sent", input, state))
```

`Input.send` is **not** gated by the enabled state. Binds are gated; direct
sends always execute.

### Low-level output

```python
Input.press("w")              # hold
Input.release("w")            # release
Input.hold("w")               # alias for press
Input.write("text", 0.01)     # Unicode typing, seconds between characters
Input.release_all()           # release everything the library is holding
```

### Mouse

```python
Input.click("lbutton")             # one click
Input.click("rbutton", count=3)    # three clicks
Input.move_to(960, 540)            # absolute screen position
Input.move(10, -5, absolute=False) # relative movement
Input.wheel(dy=-1)                 # one notch down
Input.wheel(dx=1)                  # one notch right
Input.get_position()               # (x, y)
```

Device-scoped views are available as `Input.keyboard.*` and `Input.mouse.*`,
for example `Input.mouse.press("xbutton1")`.

### Testing without injecting

```python
Input.simulate("f")     # run the binding layer as if "f" were tapped
```

`Input.simulate` feeds synthetic `InputEvent`s through the registry. It does
not create OS input and runs callbacks synchronously, which makes it useful in
tests.

### Raw events

```python
def on_event(event):
    print(event.id, event.event_type, event.device)
    return False            # True consumes the event when suppress=True

handle = Input.dispatcher.hook(on_event, device="keyboard", suppress=True)
Input.dispatcher.unhook(handle)
```

Raw hooks run on the OS hook thread, so keep them short. Bind callbacks run
on worker threads and may block; raw hooks should not.

`InputEvent` fields include `id`, `device`, `event_type`, `kind`, `scan_code`,
`vk_code`, `x`, `y`, `delta`, `injected`, and `device_id`.

---

## State and Event helpers

### `State`

`State` is an observable value. It can behave as a boolean or as a counter.

```python
ready = State()                 # False
ready = State(value=True)       # True
ready = State(value=3)          # counter 3 -> True
```

Update it:

```python
ready.update(True)              # boolean mode
ready.update(False)
counter.update(+1)              # counter mode
counter.update(-1)
counter.update(0)               # re-evaluate without changing the counter
```

Read it by calling it:

```python
ready()                         # bool / current value
```

Observe it:

```python
ready.sync(on_change)           # inline, ordered with other sync callbacks
ready.connect(on_change)        # on its own thread, in parallel
```

Both receive the **resulting** value, not the raw increment:

```python
def on_change(value: bool):
    print("ready is now", value)

ready.sync(on_change)
```

If you need the raw `update()` argument instead, use
`ready.update.sync(...)` or `ready.update.connect(...)`.

Useful `State` features:

```python
ready.wait(1000)                # wait for the opposite of the current value
ready.wait(1000, True)          # wait until True
ready.wait(1000, False)         # wait until False

with ready:                     # wait for False, set True, restore False on exit
    ...

with ready.inverse:             # wait for True, set False, restore True on exit
    ...
```

A guard can derive the value from other state:

```python
armed = State(get=lambda value: value and enabled() and Sys.state())
```

`Sys.state` is a `State` and the same object as `Input.enabled`. It is the
**intended** state: F1/F2 and `Sys.toggle()` change it. It can be true while the
system is not actually producing input because the foreground window does not
match `Sys.appId`.

`Sys.active` is another `State`, the **real** state. It is
`Sys.state and the current window matches Sys.appId`, and it is refreshed when
`Sys.state` or `window.changed` fires. Normal `Sys` binds follow `Sys.active`.
Observe it like any other state:

```python
Sys.active.sync(lambda value: print("really active:", value))
```

### `Event`

`Event` is a callable fan-out with an optional guard.

```python
changed = Event()               # every call is accepted
changed = Event(lambda value: value > 0)   # guard rejects non-positive values
```

Connect callbacks:

```python
changed.sync(callback)          # inline
changed.connect(callback)       # separate thread
changed.once(callback)          # parallel, removed after one call
changed.syncOnce(callback)      # inline, removed after one call
```

Fire it and wait for it:

```python
changed(5)

changed.wait(1000)              # next call arguments, or False on timeout
changed.wait(1000, 5)           # True when the value 5 arrives
```

`State` itself is an `Event`: its connections receive value changes. Its
`update` attribute is a second `Event` that receives the raw increments.

### Time helpers

```python
sleep(250)                      # sleep in milliseconds
delay(callback, 250)            # run callback after 250 ms, returns the thread
now()                           # current time in milliseconds
```

`sleep` and `delay` take **milliseconds**, matching the rest of the library
(`Input.wait` timeouts, buffer durations, and cooldowns).

---

## A complete build script

```python
from MacroLibrary import *

# ---------------------------------------------------------------- config
Sys.config.update({
    "appId": "Roblox",
    "binds": {"default": True},
    "rebinds": {
        ("~lalt", "lshift"),
        ("g", "v"),
        ("h", "b"),
    },
    "inputs": {
        "block": "f",
        "dash": "q",
        "aux": "ß",
        "wpn": "´",
    },
})

inputs = Sys.config["inputs"]

# ----------------------------------------------------------------- state
blocking = State()
blocking.sync(lambda value: print("blocking:", value))

# ----------------------------------------------------------------- binds
def on_block(event_id):
    Input.send(inputs["block"], True)
    blocking.update(True)
    try:
        Input.wait(event_id)
    finally:
        blocking.update(False)
        Input.send(inputs["block"], False)

def on_dash(event_id):
    Input.send(inputs["dash"])

def on_aux(event_id):
    Input.send("lbutton")

Sys.bind("f", on_block)                 # category "" -> always loaded
Sys.bind("lshift", on_dash, category="default")
Sys.bind("q", on_aux, category="default")

# ------------------------------------------------------------------ run
if __name__ == "__main__":
    Sys.load()
```

Startup output looks like:

```text
loading config
input rebinds:
  ~lalt : lshift
  g : v
  h : b
input binds
  category:
    group:
      on_block: f
  category:  default
    group:
      on_dash: lshift
      on_aux: q
active window: Roblox
-- system disabled --
loading finished
```

Then focus the target window and press F1:

```text
active window: Roblox
-- system enabled --
```

Press F12 to exit cleanly.

For an advanced example of movement state and buffered input, see
`test/run_v2.py`. That file still uses the older `Sys.bindData` registration
form described below.

---

## Updating older scripts

This checkout exposes the configuration as `Sys.config` and registers callables
with `Sys.bind`:

| Older revision | Current checkout |
|---|---|
| `config.update({...})` | `Sys.config.update({...})` |
| `config["appId"]` | `Sys.config["appId"]` |
| `Sys.bind(input, call, category=category)` |
| `from MacroLibrary import *` exports `config` | only `Sys.config`; there is no module-level `config` |

The category argument moved from the first to the last position, and the
default category is `""` instead of `"default"`. If you are running a released
build that still has `Sys.bindData`, keep using it there; the rest of the
lifecycle is unchanged.

---

## Troubleshooting

### Nothing happens even though the macro is running

Check the console first. `Sys.load()` starts with the intended state off, and
status lines print the foreground title:

```text
active window: ...
-- system disabled --
```

Press **F1** to arm the system. It stays disabled while the foreground window
does not match `Sys.appId`; the extra line tells you it is waiting:

```text
-- intended enabled , waiting for window --
```

Switch to the target window and `Sys.active` turns on automatically. If it
never enables, the title does not match `Sys.appId` exactly.

### `appId` rejects the window

The match is exact and case-sensitive against the full title:

```python
Sys.appId = "Roblox"                                   # only a window titled exactly "Roblox"
Sys.appId = None                                       # accept any window
```

A browser tab such as
`Rogue Lineage Battlegrounds | Play on Roblox - Google Chrome for Testing`
will never match `"Roblox"`. Either run the native client, set the gate to the
exact title, or disable the gate:

```python
Sys.load()
Sys.appId = None
Sys.toggle(True)       # arming now also sets Sys.active
```

### Binds work but the game ignores the output

- Make sure the target window is focused. Macros go to the foreground window.
- On Windows, a non-elevated process cannot inject into an elevated
  application (UIPI). Run both at the same integrity level.
- Prefer real key ids. Arbitrary text is sent with Unicode events, which many
  games ignore. `"ß"` and `"´"` are real key ids and are sent as physical
  layout keys.
- Try `Input.send("f24")` with the target focused and watch the console. F24
  is a harmless test key.

### A key is stuck down

Call `Input.release_all()`. `Sys.exit()` and `Input.shutdown()` also release
held keys.

### A bind fires twice or not at all

- A blocking bind replaces an older blocking bind with the same input and
  state. Registering the same blocking bind twice leaves only the newest.
- Non-blocking (`~`) binds are never replaced. Two `~` binds on the same key
  both fire.
- A chord only fires when every other key in the chord is physically down.
- A callback that blocks for the whole hold does not block other callbacks;
  each callback runs on its own thread.

### The process will not exit

`Sys.load()` starts a non-daemon lifeline thread. Press **F12** or call
`Sys.exit()`. Closing the terminal window also ends it.

### Linux permissions

The Linux backend reads `/dev/input/*` and creates a `uinput` device. Your user
needs read access to the input devices and write access to `/dev/uinput`
(typically membership in the `input` group and a udev rule). Without those,
hook installation fails or no devices are found.

---

## Platform notes

### Windows

- Global low-level keyboard and mouse hooks (`WH_KEYBOARD_LL`,
  `WH_MOUSE_LL`).
- Output uses scan-code `SendInput` (`KEYEVENTF_SCANCODE`) with the extended
  flag where needed, which works with games that ignore virtual-key or Unicode
  injection.
- Every synthetic event is tagged with an extra-info value, and injected
  events are ignored by the binding layer, so macros do not feed back into
  their own binds.
- The hook thread pumps a message loop; callbacks run elsewhere and cannot
  trip the low-level hook timeout.

### Linux

- The `Input` backend implements Linux with `evdev` for reading and `uinput`
  for writing.
- Devices are grabbed by default while the hook is installed, so the app sees
  only the events the library forwards.
- Key ids are mapped to Linux `KEY_*` codes internally.
- `Sys` reads the focused window title through X11 (`_NET_ACTIVE_WINDOW` +
  `_NET_WM_NAME`) using `python-xlib`. `pygetwindow` is not imported on Linux.
- Under **native Wayland**, windows do not publish `_NET_ACTIVE_WINDOW`; the
  title lookup returns `None`, so the `appId` gate is not applied. Run the
  game under XWayland for exact-title gating, or set `Sys.appId = None`.

### Unsupported platforms

Importing `MacroLibrary.Input` on anything other than Windows or Linux raises
`OSError` rather than silently degrading.
