"""
def _downCall(id : InputId):
    if digiInputs.get(id + " down") != None and digiInputs[id + " down"].pop() > now() - 50: return False
    active.add(id)
    if not Hotkeys.check(id): Input.send(id + modifier["down"])
    else: blocking.add(id)
    return True

def _upCall(id : InputId):
    if digiInputs.get(id + " up") != None and digiInputs[id + " up"].pop() > now() - 50: return False
    active.remove(id)
    if not id in blocking: Input.send(id + modifier["up"])
    else: blocking.remove(id)
    return True

class Input:
    down = Event(_downCall)
    up = Event(_upCall)
    
    @staticmethod
    def send(sig : InputSig):
        id : InputId
        if isinstance(sig , tuple):
            l = list(sig)
            id = l.pop(0)
            sig = tuple(l)
        else: id = sig

        state : str | None = None
        for m in ("down" , "up") : state = m if re.match(m , id) != None else state
        
        press = lambda io : kc.press(io)
        release = lambda io : kc.release(io)
        io = None

        _id = id
        id = normalize(id)
        
        if re.match("mouse" , id) != None:
            id = re.sub("mouse." , "" , id)
            io = mouse.Button[id]
            press = lambda io : mc.press(button = io)
            release = lambda io : mc.release(button = io)
        else:
            try: io = keyboard.Key[id]
            except KeyError:
                if len(id) > 2:
                    print("longer length:" , id)
                    for char in _id : Input.send(char) ; sleep()
                    return
                io = keyboard.KeyCode.from_char(id)
        
        if digiInputs.get(id) == None : digiInputs[id] = set()

        if state == "down" or state == None:
            digiInputs[id + " down"].add(now())
            press(io)
        if state == None : sleep()
        if isinstance(sig , tuple) and len(sig) > 0 : Input.send(sig)
        if state == "up" or state == None:
            digiInputs[id + " up"].add(now())
            release(io)

    @staticmethod
    def wait(id : InputId , timeout : int | None):
        event = Input.up
        if re.match("up" , id) != None: event = Input.up
        elif re.match("down" , id) != None: event = Input.down
        
        if timeout != None:
            to = now() + timeout
            id = normalize(id)
            while now() < to:
                i = event.wait(to - now())
                if i == id: return True

        return False


with keyboard.Listener(
    on_release = lambda io : None if Input.up(io.name if isinstance(io , (keyboard.Key)) else io.char if isinstance(io , keyboard.KeyCode) else io) else None,
    on_press = lambda io : None if Input.down(io.name if isinstance(io , (keyboard.Key)) else io.char if isinstance(io , keyboard.KeyCode) else io) else None,
    suppress = True
) as kl: kl.join()
"""