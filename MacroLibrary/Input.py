from .common import *
from .Structures import *
import queue

# input state handling
INPUT_IDS = {
    # Mouse
    "LButton", "RButton", "MButton", "XButton1", "XButton2",
    "WheelDown", "WheelUp", "WheelLeft", "WheelRight",

    # Control keys
    "CapsLock", "Space", "Tab", "Enter", "Escape", "Esc",
    "Backspace", "BS", "Delete", "Del", "Insert", "Ins",
    "Home", "End", "PgUp", "PgDn", "Up", "Down", "Left", "Right",

    # Modifiers
    "Shift", "LShift", "RShift",
    "Ctrl", "Control", "LCtrl", "RCtrl",
    "Alt", "LAlt", "RAlt",
    "LWin", "RWin",

    # Lock keys
    "NumLock", "ScrollLock",

    # Function keys
    "F1", "F2", "F3", "F4", "F5", "F6",
    "F7", "F8", "F9", "F10", "F11", "F12",
    "F13", "F14", "F15", "F16", "F17", "F18",
    "F19", "F20", "F21", "F22", "F23", "F24",

    # Numpad
    "Numpad0", "Numpad1", "Numpad2", "Numpad3", "Numpad4",
    "Numpad5", "Numpad6", "Numpad7", "Numpad8", "Numpad9",
    "NumpadDot", "NumpadDel", "NumpadIns",
    "NumpadClear", "NumpadUp", "NumpadDown",
    "NumpadLeft", "NumpadRight",
    "NumpadHome", "NumpadEnd",
    "NumpadPgUp", "NumpadPgDn",
    "NumpadDiv", "NumpadMult", "NumpadAdd",
    "NumpadSub", "NumpadEnter",

    # Media
    "Volume_Mute", "Volume_Down", "Volume_Up",
    "Media_Next", "Media_Prev", "Media_Stop", "Media_Play_Pause",

    # Browser
    "Browser_Back", "Browser_Forward", "Browser_Refresh",
    "Browser_Stop", "Browser_Search", "Browser_Favorites", "Browser_Home",

    # Misc
    "PrintScreen", "CtrlBreak", "Pause",
    "AppsKey", "Sleep", "Help",

    # Letters
    *[chr(c) for c in range(ord("A"), ord("Z") + 1)],

    # Digits
    *[str(i) for i in range(10)]
}
inputStates : Dict[InputId , int] = {}
inputQueue : List = []

T = TypeVar("T" , InputSig , InputId)
def normalize(i : T) -> T:
    if isinstance(i , tuple):
        l = list(i)
        for n in range(len(l)) : l[n] = normalize(l[n])
        i = tuple(l)
        return i
    
    i = i.lower()
    i = re.sub(r" down| up|{|}|~|!|$|^" , "" , str(i)) # _l|_r
    
    return i

def get(id : InputId):
    """
    Returns the physical input state of the input 'id'
    """
    id = normalize(id)
    #AHK.key_state(key_name = id.upper() , mode = "P") != 0
    v = inputStates.get(id)
    return v != None and v > 0

def update(id : InputId , incr : int):
    if inputStates.get(id) == None: inputStates[id] = 0
    inputStates[id] += incr
    #safety limiters
    if inputStates[id] < 0: inputStates[id] = 0
    if inputStates[id] > 1: inputStates[id] = 1
    #queue
    if id in inputQueue: inputQueue.remove(id)
    if incr > 0: inputQueue.insert(0 , id)

def _downCall(id : InputId):
    update(id , 1)
    return True

def _upCall(id : InputId):
    update(id , -1)
    return True

def _send(sig : InputSig):
    """
    Sends the input as virtual input, either as a singular input char when 'sig' is an InputId, or an input combination represented by the reverse order of the tuple 'sig'
    """
    
    if not isinstance(sig , str):
        length = len(sig)
        for i in range(length) : send(sig[length - i] + " Down"); sleep()
        for i in range(length) : send(sig[i] + " Up"); sleep()
        return
    AHK.send_input("{" + sig + "}")

    return True
send = Event(_send)

def resolve(id : InputId):
    """
    sends appropriate input signals to synchronize virtual and physical input states of id
    """

    id = normalize(id)
    id += " " + ("down" if get(id) else "up")
    print("resolved " + id)
    send(id)

def wait(id : InputId , timeout : int | None = None , pressed : bool | None = None):
    """
    Yields the current thread until input 'id' changes to the logical state, by default up
    """

    idstate = re.search(r"down|up" , id.lower())
    if pressed == None:
        if idstate != None: pressed = idstate[0] == "down"
        else: pressed = False

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

def buffer(id : InputId , timeout : int = 0):
    """
    sends the input in its specified state, regardless of its current state, then resolves its state automatically based on its physical state, while entirely circumventing input blocks;
    timeout in milliseconds: if specified, it will buffer the resolve until timeout, extending it if state hasn't changed
    """

    nid = normalize(id)
    s = re.search(id.lower() , " up") == None
    if s == True and re.search(id.lower() , " down") == None: id += " down"

    send(id)
    if timeout <= 0 and s != get(nid):
        resolve(nid)

    def th():
        t = now() + timeout
        if timeout > 0 and wait(nid , timeout , not s): sleep(t - now())
        else: wait(nid , not s)
        resolve(nid)
    delay(th)

down = Event(_downCall)
up = Event(_upCall)

# input binding
class Bind:
    # cls property
    set : Set[Bind] = set()

    # data property
    input : Final[Tuple[InputId , ...]]
    call : Final[Callable[[InputId]]]
    block : Final[bool]

    # dynamic property
    enabled : bool
    thread : threading.Thread | None

    def __call__(self , id : InputId) -> bool:
        if not self.enabled or (self.thread != None and self.thread.is_alive()): return False
        for i in self.input:
            if not get(i): return False

        self.thread = threading.Thread(target = lambda: self.call(id))
        self.thread.start()
        return True

    def __init__(self , input : InputId | InputSig , call : Callable[[InputId]]):
        input = input if isinstance(input , tuple) else (input,)
        normInput = normalize(input)
        id = normInput[0]

        self.input = normInput
        self.call = call
        self.block = re.match("~" , input[0]) == None

        self.enabled = False
        self.thread = None

        # commit to handlers
        self.set.add(self)
        InputConnection.get(id).add(self)

    def toggle(self , enabled : bool):
        self.enabled = enabled

class InputConnection(Set[Bind]):
    dict : Dict[InputId , InputConnection] = {}

    id : InputId
    block : State
    hotkey: None | InputId
    active : bool
    sorted : Dict[int , List[Bind]]

    @classmethod
    def get(cls , id : InputId) -> InputConnection:
        id = normalize(id)
        c = cls.dict.get(id)
        if c == None: c = cls(id)
        return c

    def add(self, element: Bind) -> None:
        res = super().add(element)
        if element.block: self.block.update(1)

        l = len(element.input)
        if not self.sorted.get(l): self.sorted[l] = []
        self.sorted[l].append(element)

        return res

    def remove(self, element: Bind) -> None:
        res = super().remove(element)
        if element.block: self.block.update(-1)

        l = len(element.input)
        self.sorted[l].remove(element)
        if len(self.sorted[l]) <= 0: self.sorted.pop(l)

        return res

    def __init__(self, id : InputId):
        super().__init__()
        self.id = normalize(id)
        self.block = State()
        self.block.connect(lambda b: self.toggle())
        self.hotkey = None
        self.active = False
        self.dict[id] = self
        self.sorted = {}

    def toggle(self , enabled : bool | None = None):
        if enabled == None: enabled = self.hotkey != None
        blocking = self.block()
        if not blocking: enabled = True
        
        hotkey = (("" if blocking else "~") + "$*" + self.id) if enabled else None
        if hotkey == self.hotkey: return
        
        if self.hotkey != None:
            
            AHK.remove_hotkey(self.hotkey)
            AHK.remove_hotkey(self.hotkey + " Up")
            self.hotkey = None

        if hotkey != None:
            # establish AHK callback chain
            self.hotkey = hotkey
            def errorHandler(msg : str , e : Exception):
                print("something went wrong at keybind " + self.id + " : " + msg)
                raise e
        
            AHK.add_hotkey(hotkey , lambda: self.down() , errorHandler)
            AHK.add_hotkey(hotkey + " Up" , lambda: self.up() , errorHandler)    

    def down(self):
        if self.active: return
        self.active = True
        id = self.id
        down(id)
        
        block = False
        if len(self.sorted) > 0:
            success = False
            def sort(b : Bind):
                priority = 0
                for i in b.input:
                    if not i in inputQueue: continue
                    priority += inputQueue.index(i)
                return priority
            for _ , l in sorted(self.sorted.items() , key = lambda p:p[0] , reverse = True):
                for b in sorted(l , key = sort):
                    if not b(id): continue
                    block = b.block
                    success = True
                    break
                if success: break
        
        #for b in sorted(self , key = lambda b: len(b.input) , reverse = True):
        #    if not b(id): continue
        #    block = b.block
        #    break
        
        if block or not self.block(): return
        
        send(id + " Down")

    def up(self):
        if not self.active: return
        id = self.id
        up(id)
        self.active = False
        if not self.block(): return

        send(id + " Up")

# launch setup
for id in INPUT_IDS: InputConnection.get(id)


Connection = InputConnection
__all__ = ["down" , "up" , "get" , "send" , "resolve" , "wait" , "buffer" , "Bind" , "Connection"]