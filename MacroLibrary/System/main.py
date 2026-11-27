from typing import Iterable
from .common import *
from . import window
import json


class Sys:
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


    state = Input.enabled
    _prevState = False
    enabled = State(value=False)
    loaded : bool = False
    appId : str | None = None
    _window_watch : bool = False

    config = Config({
        "build":    "",
        "appId":    "",

        "binds":    {},
        "inputs":   dict(),
        "rebinds":  set()
    })
    binds : Set[Input.Bind] = set()
    sysbinds : Set[Input.Bind] = set()
    _bind_data : Dict[str , List[KeybindEntry] | List[KeybindEntry]] = {}


    @classmethod
    def bind(cls , input : InputSig , call : Callable[[InputId]] , category : str = ""):
        if not cls._bind_data.get(category) : cls._bind_data[category] = []
        cls._bind_data[category].append((input , call))

        if cls.loaded:
            print("Bind added: " + call.__name__ + ":" , input)
            b = Input.bind(input , call)
            cls.binds.add(b)
            b.toggle(cls.state())


    @classmethod
    def load(cls):
        def lifeline():
            exitEvent.wait()
        threading.Thread(target = lifeline).start()
        
        print("loading config")
        if cls.config["appId"] != "": cls.appId = cls.config["appId"]

        # input rebinds
        print("input rebinds:")
        for pair in cls.config["rebinds"]:
            print("  " + pair[0] + " : " + pair[1])
            Sys.rebind(pair[0] , pair[1])

        # input binds
        print("input binds")
        for cid , category in [("" , True)] | cls.config["binds"].items():
            f = cls._bind_data.get(cid)
            if f == None: continue
            if not category: continue

            print("  category: " , cid)
            if category == True or isinstance(category , str):
                if isinstance(category , str) and isinstance(f , dict): f = f.get(category)
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

        # input hooks and binds
        Input.hook()
        for e in cls.sysbinds: e.toggle(True)
        for e in cls.binds - cls.sysbinds: e.toggle(False)

        cls.toggle(False)
        cls.loaded = True
        cls._window_watch = window.watch()
        print("loading finished")


    @classmethod
    def exit(cls) -> bool:
        if not cls.loaded: return False
        cls.toggle(False)
        if cls._window_watch:
            cls._window_watch = False
            window.unwatch()
        Input.shutdown()
        print("-- system exit --")
        exitEvent.set()
        cls.loaded = False
        return True


    @classmethod
    def toggle(cls , state : bool | None = None):
        if state == None: state = not cls.enabled()
        prev = cls.state()
        cls.enabled.update(state)

        if cls.state() == prev and cls.state() != cls.enabled():
            print("-- intended " + ("enabled" if cls.state() else "disabled") + " , waiting for window --")


    @classmethod
    def _windowMatches(cls , win = None) -> bool:
        if cls.appId == None: return True
        if win == None: win = window.getActiveWindowTitle()
        return win != None and str(win) == cls.appId


    @classmethod
    def refresh(cls):
        if cls.state() == cls._prevState: return
        cls._prevState = cls.state()

        # normal binds follow the real state; system binds always stay enabled
        for e in cls.binds - cls.sysbinds: e.toggle(cls.state())

        print(
            "active window: " + str(window.getActiveWindowTitle()) +
            "\n-- system " + ("enabled" if cls.state() else "disabled") + " --"
        )


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


Sys.state._get_ = lambda v: (v and Sys.loaded and Sys.enabled())
Sys.state.sync(lambda s: Sys.refresh())
Sys.enabled.sync(lambda _: Sys.state.update(Sys._windowMatches()))
@window.changed.sync
def onWinChange(win):
    Sys.state.update(Sys._windowMatches(win))
onWinChange(window.getActiveWindowTitle())

# sys binds
Sys.sysbinds.add(Input.Bind("F12" , lambda id : Sys.exit() , always=True))
Sys.sysbinds.add(Input.Bind("F1" , lambda id : Sys.toggle(not Sys.enabled()) , always=True))
Sys.sysbinds.add(Input.Bind("F2" , lambda id: Sys.toggle(False) , always=True))


__all__ = ["Sys"]