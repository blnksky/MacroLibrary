from .common import *
import json , pygetwindow

config = {
    "build":    "",
    "appId":    "",

    "binds":    {
        "default":  True
    },
    "inputs":   {},
    "rebinds":  {}
}

class BindData(Dict[str , Set[KeybindEntry | Set[KeybindEntry]]]):
    def update(self , category : str | Literal["default"] , input : InputSig , call : Callable[[InputId]]):
        if not self.get(category) : self[category] = set()
        self[category].add((input , call))

class Sys:
    state = State(value = False)
    loaded : bool = False
    appId : str | None = None
    
    bindData = BindData()
    callbinds : Set[Input.Bind] = set()
    sysbinds : Set[Input.Bind] = set()

    @classmethod
    def toggle(cls , state : bool | None = None):
        if state == None: state = not cls.state()

        # check active window
        win = pygetwindow.getActiveWindow()
        if win != None: win = win.title
        print("active window:" , win)
        if cls.appId != None and (win != None and str(win) != cls.appId): state = False

        cls.state.update(state)

        for e in cls.callbinds:
            if e in cls.sysbinds: e.toggle(True); continue
            e.toggle(state)
        
        for id , c in Input.Connection.dict.items():
            c.toggle(state)
        
        if not state:
            for b in cls.sysbinds: Input.Connection.get(b.input[0]).toggle(True)

        print("-- system " + ("enabled" if cls.state() else "disabled") + " --")

    @classmethod
    def loadConfig(cls , file : str):
        global config
        print("loading config data " + file + (" , build: " + config["build"]) if config["build"] != None else "")

        with open(file) as f: config |= json.load(f)

        # import build
        buildId = config["build"]
        if buildId != "":
            with open(os.path.join(os.path.dirname(file) , buildId)) as f: config |= json.load(f)

    @classmethod
    def load(cls):
        def lifeline():
            exitEvent.wait()
        threading.Thread(target = lifeline).start()

        inputs = config["inputs"]
        binds = config["binds"]
        rebinds = config["rebinds"]
        
        print("loading config")
        if config["appId"] != "": cls.appId = config["appId"]

        # setup binds
        def iter(f : Dict | List | Any):
            if isinstance(f , Dict):
                for i , r in f.items(): f[i] = iter(r)
            elif isinstance(f , list): f = tuple(f)
            return f
        iter(inputs)
        iter(binds)

        def iter1(f : Dict | List | Any):
            if isinstance(f , Dict):
                new = {}
                for i , r in f.items():
                    if isinstance(i , List): new[tuple(i)] = iter(r)
                    else: new[i] = iter(r)
                f.clear()
                f |= new
            elif isinstance(f , list): f = tuple(f)
            return f
        iter1(rebinds)
        for input , output in rebinds.items(): Sys.rebind(input , output)

        for cid , category in binds.items():
            f = cls.bindData.get(cid)

            if f == None: continue
            if category == False or category == None: continue

            print("  category: " , cid)
            if category == True or isinstance(category , str):
                f = f.get(category) if (isinstance(category , str) and isinstance(f , dict)) else f if category == True else None
                if f == None : continue

                print("    group:" , category if isinstance(category , str) else "")

                if not isinstance(f , set): return
                for (input , call) in f:
                    if not isinstance(call , Callable) or not isinstance(input , str): continue
                    print("      " + call.__name__ + ":" , input)
                    cls.callbinds.add(Input.Bind(input , call))
                
            elif isinstance(category , list):
                print("    list: ")
                for e in category:
                    if f == None: continue
                    f = f.get(e) if isinstance(f , dict) else None
                    if f == None : continue
                    print("      group: " + e)
                    if not isinstance(f , set) : return

                    for (input , call) in f:
                        print("        " + call.__name__ + ":" , input)
                        Input.Bind(input , call)
        
        AHK.start_hotkeys()
        for e in cls.sysbinds: e.toggle(True)

        cls.loaded = True
        cls.toggle(False)
        print("loading finished")

    @classmethod
    def exit(cls) -> bool:
        if not cls.loaded: return False
        cls.toggle(False)
        AHK.stop_hotkeys()
        print("-- system exit --")
        exitEvent.set()
        cls.loaded = False
        return True

    @classmethod
    def rebind(cls , input : InputSig , outputid : InputId):
        def call(id):
            Input.send(outputid + " down")
            Input.wait(id , None , False)
            Input.send(outputid + " up")
        bind = Input.Bind(input , call)
        bind.toggle(cls.state())
        cls.callbinds.add(bind)
        return bind
# sys binds
Sys.sysbinds.add(Input.Bind("F12" , lambda id : Sys.exit()))
Sys.sysbinds.add(Input.Bind("F1" , lambda id : Sys.toggle()))


__all__ = ["Sys" , "config"]