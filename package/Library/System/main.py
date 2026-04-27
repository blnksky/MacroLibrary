from .common import *
import pygetwindow

class _Keybinds(Dict[str , Dict[str , KeybindEntry | Dict[str , KeybindEntry]]]):
    def update(self , category : str , id : str , input : InputSig , call : Callable[[InputId]]):
        if not self.get(category) : self[category] = {}
        self[category][id] = (input , call)

class Sys:
    state = False
    keybinds = _Keybinds()
    callbinds = Dict[str , Input.Bind]
    appId : str | None = None
    loaded : bool = False
    sysbinds : Set[Input.Bind] = set()

    @classmethod
    def toggle(cls , state : bool | None = None):
        if state == None: state = not cls.state

        # check active window
        win = pygetwindow.getActiveWindow()
        if win != None: win = win.title
        print("active window:" , win)
        #if cls.appId != None and (win == None or win.title != cls.appId): state = False

        cls.state = state

        for e in Input.Bind.elements:
            if e in cls.sysbinds: e.toggle(True); continue
            e.toggle(state)
        print("-- system " + ("enabled" if state else "disabled") + " --")

    @classmethod
    def load(cls , build : BuildData):
        print("loading build...")
        for cid , category in build.items():
            f = cls.keybinds.get(cid)
            if f == None or not isinstance(f , dict): continue
            if category == False or category == None: continue

            print("  category: " , cid)
            if category == True or isinstance(category , str):
                f = f.get(category) if isinstance(category , str) else f if category == True else None
                if f == None : continue
                print("    group:" , category if isinstance(category , str) else None)
                if not isinstance(f , dict) : return
                
                for id , (input , call) in f.items():
                    if not isinstance(call , Callable): continue
                    Input.Bind(input , call)
                
            elif isinstance(category , list):
                print("    list: ")
                for e in category:
                    if f == None: continue
                    f = f.get(e)
                    if f == None : continue
                    print("      group: " + e)
                    if not isinstance(f , dict) : return

                    for id , (input , call) in f.items() : Input.Bind(input , call)
        
        cls.toggle()
        AHK.start_hotkeys()
        for e in cls.sysbinds: e.toggle(True)

        def lifeline():
            exitEvent.wait()
        threading.Thread(target = lifeline).start()

        cls.loaded = True
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

# sys binds
Sys.sysbinds.add(Input.Bind("F12" , lambda id : Sys.exit()))
Sys.sysbinds.add(Input.Bind("F1" , lambda id : Sys.toggle()))
