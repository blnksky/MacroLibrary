from .common import *
from .listener import *

class InputBind:
    # class property
    connections : Dict[InputId , InputConnection] = {}
    elements : Set[InputBind] = set()
    
    # instance property
    enabled : bool
    input : Tuple[InputId , ...]
    normInput : Tuple[InputId , ...]
    block : bool
    call : Callable[[InputId]]
    thread : threading.Thread | None

    def __call__(self , id : InputId) -> bool:
        if not self.enabled or (self.thread != None and self.thread.is_alive()): return False
        for i in self.normInput:
            if i != id and not get(i): return False

        self.thread = threading.Thread(target = lambda: self.call(id))
        self.thread.start()
        return True

    def __init__(self , input : InputId | InputSig , call : Callable[[InputId]]):
        input = input if isinstance(input , tuple) else (input,)
        normInput = normalize(input)
        id = normInput[0]

        # instance properties
        self.enabled = False
        self.input = input
        self.normInput = normInput
        self.call = call
        self.thread = None
        self.block = re.match("~" , input[0]) == None

        # commit to handlers
        self.elements.add(self)
        InputConnection.get(id).add(self)

    def toggle(self , enabled = False):
        self.enabled = enabled

class InputConnection(Set[InputBind]):
    elements = InputBind.connections

    id : InputId
    active : bool

    @classmethod
    def get(cls , id : InputId):
        if not cls.elements.get(id) : cls.elements[id] = cls(id)
        return cls.elements[id]

    def __init__(self, id : InputId):
        super().__init__()
        self.id = normalize(id)

        def errorHandler(msg : str , e : Exception):
            print("something went wrong at keybind " + self.id + " : " + msg)
            raise e
        
        # establish AHK callback chain
        AHK.add_hotkey("$*" + self.id , lambda: self.down() , errorHandler)
        AHK.add_hotkey("$*~" + self.id + " Up" , lambda: self.up() , errorHandler)

    def down(self):
        if self.active: return
        self.active = True

        id = self.id
        down._call(id)

        block = False
        for b in sorted(self , key = lambda b: len(b.input) , reverse = True):
            if not b(id): continue
            block = not b.block
            break
        
        if not block: send(id + " Down")
        wait(id)
        if not block: send(id + " Up")

    def up(self):
        if not self.active: return
        self.active = False

        id = self.id
        up._call(id)

Bind = InputBind
__all__ = ["Bind"]
