from .common import *
from .Structures import *
import queue

import keyboard
import mouse


## Sys properties
enabled = State(value=False)


## input identification
KEY_TO_AHK = {
    # Letters
    0x01E: "a",
    0x030: "b",
    0x02E: "c",
    0x020: "d",
    0x012: "e",
    0x021: "f",
    0x022: "g",
    0x023: "h",
    0x017: "i",
    0x024: "j",
    0x025: "k",
    0x026: "l",
    0x032: "m",
    0x031: "n",
    0x018: "o",
    0x019: "p",
    0x010: "q",
    0x013: "r",
    0x01F: "s",
    0x014: "t",
    0x016: "u",
    0x02F: "v",
    0x011: "w",
    0x02D: "x",
    0x015: "y",
    0x02C: "z",

    # Number row
    0x002: "1",
    0x003: "2",
    0x004: "3",
    0x005: "4",
    0x006: "5",
    0x007: "6",
    0x008: "7",
    0x009: "8",
    0x00A: "9",
    0x00B: "0",

    # Function keys
    0x03B: "f1",
    0x03C: "f2",
    0x03D: "f3",
    0x03E: "f4",
    0x03F: "f5",
    0x040: "f6",
    0x041: "f7",
    0x042: "f8",
    0x043: "f9",
    0x044: "f10",
    0x057: "f11",
    0x058: "f12",

    # Special keys
    0x001: "esc",
    0x00E: "backspace",
    0x00F: "tab",
    0x01C: "enter",
    0x039: "space",
    0x03A: "capslock",

    # Modifiers
    0x02A: "shift",
    0x02A: "lshift",
    0x036: "rshift",
    0x01D: "ctrl",
    0x01D: "lctrl",
    0x01D: "rctrl",
    0x038: "alt",

    # Punctuation (physical positions)
    0x00C: "-",
    0x00D: "=",
    0x01A: "[",
    0x01B: "]",
    0x027: ";",
    0x028: "'",
    0x029: "`",
    0x02B: "\\",
    0x033: ",",
    0x034: ".",
    0x035: "/",

    # Numpad
    0x045: "numlock",
    0x037: "numpadmult",
    0x04A: "numpadsub",
    0x04E: "numpadadd",
    0x053: "numpaddot",

    0x052: "numpad0",
    0x04F: "numpad1",
    0x050: "numpad2",
    0x051: "numpad3",
    0x04B: "numpad4",
    0x04C: "numpad5",
    0x04D: "numpad6",
    0x047: "numpad7",
    0x048: "numpad8",
    0x049: "numpad9",


    ## Extended keys
    # Navigation
    "home": "home",
    "up": "up",
    "page up": "pgup",
    "left": "left",
    "right": "right",
    "end": "end",
    "down": "down",
    "page down": "pgdn",
    "insert": "insert",
    "delete": "delete",

    # Numpad
    "num enter": "numpadenter",
    "divide": "numpaddiv",

    # misc
    "left windows": "lwin",
    "right windows": "rwin",
    "menu": "appskey",
    "print screen": "printscreen",
}
AHK_TO_KEY = {}
for i , e in KEY_TO_AHK.items(): AHK_TO_KEY[e] = i

# Mouse Buttons
MOUSE_TO_AHK = {
    "left": "lbutton",
    "right": "rbutton",
    "middle": "mbutton",
    "x": "xbutton1",
    "x2": "xbutton2",
}
AHK_TO_MOUSE = {}
for i , e in MOUSE_TO_AHK.items(): AHK_TO_MOUSE[e] = i

INPUT_IDS = set(AHK_TO_KEY.keys()) | set(AHK_TO_MOUSE.keys())

# Passthrough Inputs
PASSTHROUGH_INPUTS = {
    "lbutton", "rbutton", "mbutton", "xbutton1", "xbutton2",
    "wheeldown", "wheelup", "wheelleft", "wheelright"
}


## input state handling
inputStates : Dict[InputId , int] = {}
inputQueue : List = []
rebinds : Dict[InputSig , Set[InputSig]] = {}


## input buffer
hotkeyBuffer = 100
stateTS : Dict[InputId , int] = dict()
def th():
    while not exitEvent.wait(hotkeyBuffer * 10):
        garb = set()
        for i , t in stateTS.items(): garb.add(i) if now() - t > hotkeyBuffer else None
        for i in garb: stateTS.pop(i)
Thread(target=th).start()

@overload
def last(id : InputId) -> Tuple[bool , int]:
    """
    returns the last input state change if recorded, else a default tuple
    """
@overload
def last(id : InputId , state : bool) -> int:
    """
    returns the time of the last corresponding input state change if recorded, else 0
    """
def last(id : InputId , state = None):
    id = normalize(id)
    if state != None:
        i = id + " " + ("down" if state else "up")
        return stateTS[i] if i in stateTS else 0 
    else:
        t1 = last(id , True)
        t2 = last(id , False)
        c = t1 >= t2
        return (c , t1 if c else t2)


## features
T = TypeVar("T" , InputSig , InputId)
def normalize(input : T , state : bool = True , passthrough : bool = True , rebinding : bool = True) -> T:
    if isinstance(input , tuple):
        inp = ()
        for idx in range(len(input)): inp = inp + (normalize(input[idx]),)
        input = inp
    elif isinstance(input , str):
        input = input.lower()
        s = re.sub(" down| up" , "" , input)
        
        ex = r"{|}|!|$|^" + ("| down| up" if state else "") + ("|~" if passthrough else "") + ("|#" if rebinding else "")
        input = re.sub(ex , "" , input.lower())
        if input == "" and len(s) > 0: input = s[-1]
    return input

def compile(input : InputSig) -> Tuple[InputId , ...]:
    if isinstance(input , str):
        input = tuple(re.split(r" , " , input))
    l = []
    for i in input: l.append(i.lower())
    input = tuple(l)
    return input

def isInput(input : InputSig):
    for i in compile(input):
        if not normalize(i) in INPUT_IDS: return False
    return True

def get(input : InputSig) -> bool:
    """
    Returns the physical input state of the input 'id'
    """
    input = normalize(compile(input))
    for id in input:
        v = inputStates.get(id)
        if v == None or v <= 0: return False
    return True

def update(id : InputId , incr : int):
    if inputStates.get(id) == None: inputStates[id] = 0
    inputStates[id] += incr
    #safety limiters
    if inputStates[id] < 0: inputStates[id] = 0
    if inputStates[id] > 1: inputStates[id] = 1
    #queue
    if id in inputQueue:
        inputQueue.remove(id)
    if incr > 0:
        inputQueue.insert(0 , id)
        stateTS[id + " down"] = now()
    else:
        stateTS[id + " up"] = now()

def _downCall(id : InputId):
    update(id , 1)
    return True

def _upCall(id : InputId):
    update(id , -1)
    return True

def _send(input : InputSig , state : bool | None = None , rebinding : bool = False , stateDelay : int | None = None):
    """
    Sends the input as virtual input in the specified down/up state, either as a singular input char when 'sig' is an InputId, or an input combination represented by the reverse order of the tuple 'sig'.
    Input string may contain modifier prefixes like '#' (translates input into respective rebinds) or suffixes like ' down' or ' up' (specifying input state)
    """

    if not enabled(): return False

    if isinstance(input , str) and re.search(" , " , input) != None: input = compile(input)
    prfx = input[0] if isinstance(input , tuple) else input
    f = re.search("#" , prfx)
    rebinding = rebinding or (f != None and f[0] != normalize(prfx))

    if rebinding:
        inp = compile(input)
        if state == None:
            s = re.search(r" down| up" , inp[0])
            state = None if s == None else s[0] == " down"
        inp = normalize(inp)
        if inp in rebinds.keys():
            for i in rebinds[inp]: send(i , state=state , rebinding=False , stateDelay=stateDelay) if i != inp else None
            return
    if isinstance(input , tuple):
        if len(input) == 1: _send(input[0] , state=state , rebinding=rebinding , stateDelay=stateDelay); return True
        if state != None:
            for i in input: _send(i , state=state , rebinding=rebinding)
        else:
            for i in reversed(input):
                if re.search(r" down| up" , i) != None: _send(i , rebinding=rebinding); continue
                _send(i + " down" , rebinding=rebinding)
            if stateDelay != None: sleep(stateDelay)
            for i in input:
                if re.search(r" down| up" , i) != None: continue
                _send(i + " up" , rebinding=rebinding)
    elif isinstance(input , str):
        if isInput(input):
            i = normalize(input)
            
            sm = re.search(r" down | up" , input)
            if state == None and sm != None: state = {" down":True," up":False}.get(sm.string)

            if stateDelay != None:
                _send(input , True)
                sleep(stateDelay)
                _send(input , False)
                return

            if i in AHK_TO_MOUSE:
                c = AHK_TO_MOUSE[i]
                if state == None: mouse.press(c)
                elif state: mouse.hold(c)
                else: mouse.release(c)
            elif i in AHK_TO_KEY:
                c = AHK_TO_KEY[i]
                if state == None or state: keyboard.press(c)
                if state == None or not state: keyboard.release(c)
        else: keyboard.write(input)

    return True
send = Event(_send)

def resolve(input : InputSig):
    """
    sends appropriate input signals to synchronize virtual and physical input states of id
    """
    input = normalize(compile(input) , True , True , False)
    for id in input: send(id + " " + ("down" if get(normalize(id)) else "up"))

def wait(id : InputId , timeout : int | None = None , pressed : bool | None = None):
    """
    Yields the current thread until input 'id' changes to the logical state, by default up. Returns the input state received if timeout isn't stated, otherwise timeout occurrence as a bool.
    """

    idstate = re.search(r" down| up" , id.lower())
    if pressed == None:
        if idstate != None: pressed = idstate[0] == " down"
        else: pressed = not get(id)

    id = normalize(id)
    if pressed == get(id): return True
    
    event = down if pressed else up
    ts = None
    if timeout != None:
        ts = now() + timeout
        while now() < ts and event.wait(ts - now()) != id: pass
    else:
        while event.wait() != id: pass
    
    return get(id) == pressed

def toggle(id : InputId , timeout : int = 0):
    """
    sends the input in its specified state, regardless of its current state, then resolves its state automatically based on its physical state, while entirely circumventing input blocks;
    timeout in milliseconds: if specified, it will buffer the resolve until timeout, extending it if state hasn't changed
    """
    nid = normalize(id)
    s = (re.search(" up" , id.lower()) == None)
    if s == True and re.search(" down" , id.lower()) == None: id += " down"

    send(id)
    if timeout <= 0 and s != get(nid):
        resolve(id)
        return

    def th():
        t = now() + timeout
        if timeout > 0 and wait(nid , timeout , not s): sleep(t - now())
        else: wait(nid , None , not s)
        resolve(id)
    delay(th)

def trigger(id : InputId , delay : int = 0):
    """
    sends respective counter state signals before sending the actual signal, delayed by delay
    """

    nid = normalize(id , rebinding=False)
    s = (re.search(" up" , id.lower()) == None)
    if s == True and re.search(" down" , id.lower()) == None: id += " down"
    send(nid + " " + ("up" if s else "down"))
    sleep(delay)
    send(id)

down = Event(_downCall)
up = Event(_upCall)


## input binding
class Bind:
    # cls property
    set : Set[Bind] = set()
    _callchains : Dict[Bind , List[Bind]] = {}
    _threadBinds : Dict[Thread , Bind] = {}

    # data property
    input : Final[Tuple[InputId , ...]]
    call : Final[Callable[[InputId]]]
    block : Final[bool]
    eventState : bool = True

    # obj property
    _lock : threading.Lock

    # dynamic property
    enabled : bool
    active : bool

    def __call__(self , id : InputId) -> bool:
        if id != self.input[0]:
            i = self.input[0]
            if now() - last(i , True) <= hotkeyBuffer: self(i)
            return False
        if not self.enabled: return False
        for i in self.input:
            if get(i) or (now() - last(i , False) <= hotkeyBuffer): continue
            return False
        
        with self._lock:
            if self.active: return False
            self.active = True

        def f():
            try: self.call(id)
            finally:
                with self._lock: self.active = False
        self.thread = Thread(target=f)
        self.thread.start()

        return True

    def __init__(self , input : InputId | InputSig , call : Callable[[InputId]]):
        input = compile(input)
        normInput = normalize(input)
        id = normInput[0]
        call = matchParams(lambda id:None , call)

        self.input = normInput
        self.call = call
        self.block = re.match("~" , input[0]) == None
        if re.search(r" up" , input[0]) != None: self.eventState = False

        self._lock = threading.Lock()

        self.enabled = False
        self.active = False

        # commit to handlers
        self.set.add(self)
        for i in self.input: InputConnection.get(i).add(self) if i == id else InputConnection.get(i).peripheral.add(self)

    def toggle(self , enabled : bool):
        self.enabled = enabled

class InputConnection(Set[Bind]):
    # class
    dict : Dict[InputId , InputConnection] = {}

    # obj
    id : InputId
    enabled : bool
    block : State
    active : bool
    blocked : bool
    blockhook : Callable | None

    sorted : Dict[int , List[Bind]]
    sortedUp : Dict[int , List[Bind]]
    blockDict : Dict[InputSig , Bind]
    peripheral : Set[Bind]

    @classmethod
    def get(cls , id : InputId) -> InputConnection:
        id = normalize(id)
        c = cls.dict.get(id)
        if c == None: c = cls(id)
        return c

    def add(self, element : Bind) -> None:
        res = super().add(element)
        if element.block: self.block.update(1)

        l = len(element.input)
        f = self.sorted if element.eventState else self.sortedUp
        if not f.get(l): f[l] = []
        f[l].append(element)

        # overwrite overlapping binds
        if element.block:
            prev = self.blockDict.get(element.input)
            if prev != None and prev in f[l]: self.remove(prev)
            self.blockDict[element.input] = element

        return res

    def remove(self, element: Bind) -> None:
        res = super().remove(element)
        if element.block: self.block.update(-1)

        l = len(element.input)
        self.sorted[l].remove(element)
        if len(self.sorted[l]) <= 0: self.sorted.pop(l)

        if element.block: self.blockDict.pop(element.input)

        return res

    def __init__(self, id : InputId):
        super().__init__()
        
        self.id = normalize(id)
        self.enabled = False
        self.block = State(get = lambda s: s and (not id in PASSTHROUGH_INPUTS))
        self.block.connect(lambda b: self.toggle())
        self.active = False
        self.blocked = False
        self.blockhook = None

        self.sorted = {}
        self.sortedUp = {}
        self.blockDict = {}
        self.peripheral = set()

        self.dict[id] = self

    def toggle(self , enabled : bool | None = None):
        id = self.id
        if enabled == None: enabled = not self.enabled
        if not self.block(): enabled = True
        self.enabled = enabled

        if id in AHK_TO_KEY:
            if self.enabled and self.block():
                if self.blockhook == None: self.blockhook = keyboard.block_key(AHK_TO_KEY[id])
            elif self.blockhook != None:
                keyboard.unhook(self.blockhook); self.blockhook = None

    def launch(self , eventState : bool) -> bool:
        f = self.sorted if eventState else self.sortedUp
        if len(f) <= 0: return False

        id = self.id
        def sort(b : Bind):
            priority = 0
            for i in b.input:
                if not i in inputQueue: continue
                priority += inputQueue.index(i)
            return priority

        for _ , l in sorted(f.items() , key = lambda p:p[0] , reverse = False):
            for b in sorted(l , key = sort): b(id) if not b.block else None

        for _ , l in sorted(f.items() , key = lambda p:p[0] , reverse = True):
            for b in sorted(l , key = sort):
                if not b.block or not b(id): continue
                return True
            
        return False

    def down(self):
        if self.active: return
        self.active = True
        id = self.id

        down(id)
        block = self.launch(True)
        for b in self.peripheral: b(id)

        if block or not self.block():
            self.blocked = True
            return
        
        send(id , True)

    def up(self):
        if not self.active: return
        self.active = False
        id = self.id

        up(id)
        block = self.launch(False)

        if self.blocked or not self.block():
            self.blocked = False
            return
        if block: return
        
        send(id , False)


## hooks
keyboardhook = None
def keyboardHandlerInner(event : keyboard.KeyboardEvent):
    try:
        id = KEY_TO_AHK[event.scan_code]
        c = InputConnection.get(id)
        if not c.enabled: return

        if event.event_type == "down": c.down()
        elif event.event_type == "up": c.up()

        if not c.block(): return
        else: return False
    except Exception:
        unhook()
        print(Exception)
def keyboardHandler(event : keyboard.KeyboardEvent):
    r = keyboardHandlerInner(event)
    if r != None: return

    t = event.event_type
    c = event.scan_code
    if t == "down" or t == None: keyboard.press(c)
    if t == "up" or t == None: keyboard.release(c)

mousehook = None
def mouseHandler(event : mouse.ButtonEvent):
    try:
        if not isinstance(event , mouse.ButtonEvent): return 

        if event.button == None: return

        id = MOUSE_TO_AHK[event.button]
        c = InputConnection.get(id)
        if not c.enabled: return

        if event.event_type == "down": c.down()
        elif event.event_type == "up": c.up()

        if not c.block(): return
        else: return False
    except Exception:
        unhook()
        print(Exception)

def hook():
    global keyboardhook , mousehook
    if keyboardhook != None or mousehook != None: unhook()

    keyboardhook = keyboard.hook(keyboardHandler , suppress=True)
    mousehook = mouse.hook(mouseHandler)

def unhook():
    global keyboardhook , mousehook
    if keyboardhook != None: keyboard.unhook(keyboardhook); keyboardhook = None
    if mousehook != None: mouse.unhook(mousehook); mousehook = None


## misc
def rebind(input : InputSig , output : InputSig) -> Bind:
    input = compile(input)
    st = re.search(r" down| up" , input[0].lower()) 
    state = None if st == None else st[0] == " down"

    call : Callable[[InputId] , None]
    if not isInput(output) or state != None:
        def f(id): send(output)
        call = f
    else:
        output = compile(output)
        def f(id):
            send(tuple(reversed(output)) , state=True)
            wait(id , None , False)
            send(output , state=False)
        call = f
        k = normalize(input , state=False)
        if not rebinds.get(k): rebinds[k] = set()
        rebinds[k].add(output)
    return Bind(input , call)

def simulate(id : InputId):
    """
        simulates inputs as physical, making them trigger any physical input related events in this system (while ignoring physical state changes due to functional liability) (watch out for recursive loops)
    """

    c = InputConnection.dict.get(normalize(id))
    if c == None: send(id); return
    s = re.search(r" down| up" , id.lower())
    if s != None: s = s[0]

    if s in (None , " down"): c.launch(True)
    if s in (None , " up"): c.launch(False)
    if c.block(): send(id)

bufferDuration : int = 150
bufferInterval : int = 25
def buffer(inp : InputSig , duration : int | None = None , interval : int | None = None) -> Bind:
    duration = duration or bufferDuration
    interval = interval or bufferInterval
    inp = compile(inp)
    inp = normalize(inp , False)
    s = State()

    def l(i = inp , interval = interval):
        if not s(): return
        while s(): send(i , rebinding = True); sleep(interval)

    s.connect(lambda s: l())
    def f(i , s = s , duration = duration): s.update(1); wait(i); sleep(duration); s.update(-1)
    tl = list(inp)
    tl[0] = f"~{tl[0]}"
    inp = tuple(tl)
    return Bind(inp , f)


# launch setup
for id in INPUT_IDS: InputConnection.get(id)


Connection = InputConnection
__all__ = [
    "enabled",
    "normalize", "compile", "isInput",
    "down", "up", "get", "send", "resolve", "wait",
    "hotkeyBuffer", "toggle", "trigger",

    "hook", "unhook",

    "rebind", "simulate",
    "buffer", "bufferDuration", "bufferInterval",
    "Bind", "Connection",
]