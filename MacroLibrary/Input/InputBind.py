<<<<<<< HEAD
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

        self.thread = threading.Thread(target = lambda: self.call(id)).start()
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
    id : InputId
    elements = InputBind.connections

    @classmethod
    def get(cls , id : InputId):
        if not cls.elements.get(id) : cls.elements[id] = cls(id)
        return cls.elements[id]

    def __init__(self, id : InputId):
        super().__init__()
        self.id = id

        def errorHandler(msg : str , e : Exception):
            print("something went wrong at keybind " + self.id + " : " + msg)
            raise e
        
        # establish AHK callback chain
        AHK.add_hotkey("$*" + self.id , lambda: self() , errorHandler)

    def __call__(self):
        id = normalize(self.id)
        block = False
        for b in sorted(self , key = lambda b: len(b.input) , reverse = True):
            if not b(id): continue
            block = not b.block
            break
        if block: return

        send(id + " Down")
        wait(id)
        send(id + " Up")

Bind = InputBind
__all__ = ["Bind"]
=======
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

        self.thread = threading.Thread(target = lambda: self.call(id)).start()
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
    id : InputId
    elements = InputBind.connections

    @classmethod
    def get(cls , id : InputId):
        if not cls.elements.get(id) : cls.elements[id] = cls(id)
        return cls.elements[id]

    def __init__(self, id : InputId):
        super().__init__()
        self.id = id

        def errorHandler(msg : str , e : Exception):
            print("something went wrong at keybind " + self.id + " : " + msg)
            raise e
        
        # establish AHK callback chain
        AHK.add_hotkey("$*" + self.id , lambda: self() , errorHandler)

    def __call__(self):
        id = normalize(self.id)
        block = False
        for b in sorted(self , key = lambda b: len(b.input) , reverse = True):
            if not b(id): continue
            block = not b.block
            break
        if block: return

        send(id + " Down")
        wait(id)
        send(id + " Up")

Bind = InputBind
__all__ = ["Bind"]
>>>>>>> 22514187589849295d4fb64b5b37e78e37f7fa80
