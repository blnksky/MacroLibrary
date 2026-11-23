from .common import *
import queue

#import keyboard
#import mouse
from . import UnifiedInput as uin


## Sys properties
enabled = State(value=False)


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
        if not normalize(i) in uin.IIDS : return False
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
                _send(input , not state)
                sleep(stateDelay)
                _send(input , state)
            else:
                if state == None or state: uin.press(i)
                if state == None or not state: uin.release(i)
        else: uin.write(input)

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
        self.block = State()
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


## Input Hook
inputhook = None
def inputHandler(event : uin.InputEvent):
    try:
        if event.id == "mousemove": return False

        id = event.id
        c = InputConnection.get(id)
        if not c.enabled: return False

        if event.event_type == "down": c.down()
        elif event.event_type == "up": c.up()

        # suppression state
        return c.block()
    except Exception:
        unhook()
        print(Exception)

def hook():
    global inputhook
    if inputhook != None: unhook()
    inputhook = uin.hook(inputHandler , suppress=True)

def unhook():
    global inputhook
    if inputhook != None: uin.unhook(inputhook); inputhook = None


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
        rev = tuple(reversed(output))
        def f(id):
            send(rev , state=True)
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
for id in uin.IIDS: InputConnection.get(id)


Connection = InputConnection
__all__ = [
    "uin",

    "enabled",
    "normalize", "compile", "isInput",
    "down", "up", "get", "send", "resolve", "wait",
    "hotkeyBuffer", "toggle", "trigger",

    "hook", "unhook",

    "rebind", "simulate",
    "buffer", "bufferDuration", "bufferInterval",
    "Bind", "Connection",
]