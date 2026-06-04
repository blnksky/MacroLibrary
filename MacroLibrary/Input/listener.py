from .common import *

inputStates : Dict[InputId , int] = {}

idTranslations : Dict[InputId , InputId] = {
    "shift" : "LShift",
    "shift_l" : "LShift",
    "shift_r" : "RShift",
    "ctrl" : "LCtrl",
    "ctrl_l" : "LCtrl",
    "ctrl_r" : "RCtrl",
    "alt" : "LAlt",
    "alt_l" : "LAlt",
    "alt_r" : "RAlt",

    "left" : "LButton",
    "right" : "RButton",
    "middle" : "MButton",
    "x1" : "XButton1",
    "x2" : "XButton2",
}

def update(id : InputId , incr : int):
    if inputStates.get(id) == None: inputStates[id] = 0
    inputStates[id] += incr
    #safety limiters
    if inputStates[id] < 0: inputStates[id] = 0
    if inputStates[id] > 1: inputStates[id] = 1

def check(id : InputId):
    id = normalize(id)
    if not id in sent: return True
    sent.remove(id)
    return False

def _downCall(id : InputId):
    if not check(id): return False
    update(id , 1)
    return True

def _upCall(id : InputId):
    if not check(id): return False
    update(id , -1)
    return True

down = Event(_downCall)
up = Event(_upCall)

def get(id : InputId):
    """
    Returns the physical input state of the input 'id'
    """
    id = normalize(id)
    #AHK.key_state(key_name = id.upper() , mode = "P") != 0
    v = inputStates.get(id)
    return v != None and v > 0

def wait(id : InputId , timeout : int | None = None , pressed : bool | None = None):
    """
    Yields the current thread until input 'id' changes to the logical state, by default up
    """

    id = normalize(id)
    if pressed == get(id): return True
    elif pressed == None: pressed = not get(id)
    event = down if pressed else up

    ts = None
    if timeout != None:
        ts = now() + timeout
        while now() < ts and event.wait(ts - now()) != id: pass
    else:
        while event.wait() != id: pass
    
    return get(id) == pressed

keyboardListener : keyboard.Listener | None = None
mouseListener : mouse.Listener | None = None

class Listener:
    keyboard : keyboard.Listener | None = None
    mouse : mouse.Listener | None = None

    @classmethod
    def start(cls):
        def getId(io : keyboard.Key | keyboard.KeyCode | mouse.Button | None) -> str:
            if io == None: return ""

            id : str = ""
            if isinstance(io , keyboard.KeyCode): id = io.char if io.char != None else ""
            elif isinstance(io , keyboard.Key): id = io.name
            elif isinstance(io , mouse.Button): id = io.name
            else: id = io
            
            trans = idTranslations.get(normalize(id))
            if trans != None: id = trans

            return normalize(id)
        
        def kdown(io : keyboard.Key | keyboard.KeyCode | None):
            id = getId(io)
            if id == "": return
            down(id)

        def kup(io : keyboard.Key | keyboard.KeyCode | None):
            id = getId(io)
            if id == "": return
            up(id)

        def mEvent(x , y , io : mouse.Button , state):
            id = getId(io)
            if id == "": return
            down(id) if state else up(id)

        kl = keyboard.Listener(
            on_press = kdown,
            on_release = kup
        )
        cls.keyboard = kl

        ml = mouse.Listener(
            on_click = mEvent
        )
        cls.mouse = ml

        threading.Thread(target = lambda: exitEvent.wait() or kl.stop()).start()
        threading.Thread(target = lambda: kl.start()).start()

        threading.Thread(target = lambda: exitEvent.wait() or ml.stop()).start()
        threading.Thread(target = lambda: ml.start()).start()

    @classmethod
    def stop(cls):
        if cls.keyboard != None:
            cls.keyboard.stop()
            cls.keyboard = None
        if cls.mouse != None:
            cls.mouse.stop()
            cls.mouse = None


__all__ = ["down" , "up" , "get" , "wait" , "Listener"]