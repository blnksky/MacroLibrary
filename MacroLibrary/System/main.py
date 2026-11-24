from typing import Iterable
from .common import *
import json , pygetwindow


class Config(Dict):
    def load(self , file : str):
        data : Dict[str , Any] = {
            "binds":    {},
            "inputs":   {},
            "rebinds":  {}
        }
        print("loading config data " + file + (" , build: " + self["build"]) if self["build"] != None else "")

        with open(file) as f: updateDict(data , json.load(f))

        # import build
        buildId = self["build"]
        if buildId != "":
            with open(os.path.join(os.path.dirname(file) , buildId)) as f: updateDict(data , json.load(f))
        
        if data.get("rebinds") != None:
            rebinds = set()
            f = data.pop("rebinds")
            if isinstance(f , list):
                for i in f: rebinds.add(tuple(i))
            elif isinstance(f , dict):
                for i , o in f.items(): rebinds.add((i , o))
            data["rebinds"] = rebinds
        self.update(data)

    def update(self , upd):
        updateDict(self , upd)
    
    def __init__(self: dict[bytes, bytes], data : dict) -> None:
        super().__init__()
        updateDict(self , data)

config = Config({
    "build":    "",
    "appId":    "",

    "binds":    {
        "default":  True
    },
    "inputs":   dict(),
    "rebinds":  set()
})

class BindData(Dict[str , List[KeybindEntry | List[KeybindEntry]]]):
    def update(self , category : str | Literal["default"] , input : InputSig , call : Callable[[InputId]]):
        if not self.get(category) : self[category] = []
        self[category].append((input , call))

class Sys:
    state = Input.enabled
    loaded : bool = False
    appId : str | None = None
    
    bindData = BindData()
    binds : Set[Input.Bind] = set()
    sysbinds : Set[Input.Bind] = set()

    @classmethod
    def toggle(cls , state : bool | None = None):
        if state == None: state = not cls.state()

        # check active window
        win = pygetwindow.getActiveWindow()
        if win != None: win = win.title
        print("active window:" , win)
        if cls.appId != None and (win != None and str(win) != cls.appId): state = False

        # Binds now own their own enabled flag; connections no longer suppress
        # events wholesale, so there is no second pass to keep in sync.
        for e in cls.binds:
            if e in cls.sysbinds: continue
            e.toggle(state)

        # System binds stay enabled so F1 can always re-enable the system.
        for b in cls.sysbinds: b.toggle(True)

        cls.state.update(state)
        print("-- system " + ("enabled" if cls.state() else "disabled") + " --")

    @classmethod
    def load(cls):
        def lifeline():
            exitEvent.wait()
        threading.Thread(target = lifeline).start()
        
        print("loading config")
        if config["appId"] != "": cls.appId = config["appId"]

        # input rebinds
        print("input rebinds:")
        for pair in config["rebinds"]:
            print("  " + pair[0] + " : " + pair[1])
            Sys.rebind(pair[0] , pair[1])

        # input binds
        print("input binds")
        for cid , category in config["binds"].items():
            f = cls.bindData.get(cid)

            if f == None: continue
            if category == False or category == None: continue

            print("  category: " , cid)
            if category == True or isinstance(category , str):
                f = f.get(category) if (isinstance(category , str) and isinstance(f , dict)) else f if category == True else None
                if f == None : continue

                print("    group:" , category if isinstance(category , str) else "")

                if not isinstance(f , list): return
                for (input , call) in f:
                    if not isinstance(call , Callable): continue
                    print("      " + call.__name__ + ":" , input)
                    cls.binds.add(Input.Bind(input , call))
                
            elif isinstance(category , list):
                print("    list: ")
                for e in category:
                    if f == None: continue
                    f = f.get(e) if isinstance(f , dict) else None
                    if f == None : continue
                    print("      group: " + e)
                    if not isinstance(f , list) : return

                    for (input , call) in f:
                        print("        " + call.__name__ + ":" , input)
                        cls.binds.add(Input.Bind(input , call))

        Input.hook()
        for e in cls.sysbinds: e.toggle(True)

        cls.loaded = True
        cls.toggle(False)
        print("loading finished")

    @classmethod
    def exit(cls) -> bool:
        if not cls.loaded: return False
        cls.toggle(False)
        Input.shutdown()
        print("-- system exit --")
        exitEvent.set()
        cls.loaded = False
        return True

    @classmethod
    def rebind(cls , input : InputSig , output : InputSig):
        bind = Input.rebind(input , output)
        bind.toggle(cls.state())
        cls.binds.add(bind)
        return bind

    @classmethod
    def buffer(cls , inp : InputSig , duration : int | None = None , interval : int | None = None):
        bind = Input.buffer(inp , duration=duration , interval=interval)
        bind.toggle(cls.state())
        cls.binds.add(bind)
        return bind

    
# sys binds
Sys.sysbinds.add(Input.Bind("F12" , lambda id : Sys.exit() , always=True))
Sys.sysbinds.add(Input.Bind("F1" , lambda id : Sys.toggle() , always=True))
Sys.sysbinds.add(Input.Bind("F2" , lambda id: Sys.toggle(False) , always=True))


__all__ = ["Sys" , "config"]