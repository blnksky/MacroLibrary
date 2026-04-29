from .common import *

inputStates : Dict[InputId , int] = {}

def update(id : InputId , incr : int):
    if inputStates.get(id) == None: inputStates[id] = 0
    inputStates[id] += incr
    #safety patch
    if inputStates[id] < 0: inputStates[id] = 0
    if inputStates[id] > 1: inputStates[id] = 1

def _downCall(id : InputId):
    update(id , 1)
    return True

def _upCall(id : InputId):
    update(id , -1)
    return True

down = Event(_downCall)
up = Event(_upCall)

def get(id : InputId):
    """
    Returns the physical input state of the input 'id'
    """
    #AHK.key_state(key_name = id.upper() , mode = "P") != 0
    v = inputStates.get(id)
    return v != None and v > 0

def wait(id : InputId , timeout : int | None = None , pressed : bool | None = None):
    """
    Yields the current thread until input 'id' changes to the logical state, by default up
    """
    if pressed == get(id): return True
    elif pressed == None: pressed = not get(id)

    waiting = True
    def f(): waiting = False
    if timeout != None: delay(f , timeout)

    event = down if pressed else up
    while waiting:
        if event.wait() == id: return True

    return get(id)

def start():
    def getKey(io : keyboard.Key | keyboard.KeyCode | None) -> str:
        if io == None: return ""

        id : str = ""
        if isinstance(io , (keyboard.Key)): id = io.name
        elif isinstance(io , keyboard.KeyCode): id = io.char if io.char != None else ""
        else: id = io
        
        return normalize(id)

    def kdown(io : keyboard.Key | keyboard.KeyCode | None):
        id = getKey(io)
        if id == "": return
        down(id)

    def kup(io : keyboard.Key | keyboard.KeyCode | None):
        id = getKey(io)
        if id == "": return
        up(id)

    kl = keyboard.Listener(
        on_release = kup,
        on_press = kdown
    )

    threading.Thread(target = lambda: exitEvent.wait() or kl.stop()).start()
    threading.Thread(target = lambda: kl.start()).start()
start()

__all__ = ["down" , "up" , "get" , "wait"]
