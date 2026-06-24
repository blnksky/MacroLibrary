from .common import *

T = TypeVarTuple("T")
G = TypeVarTuple("G")
class Event(Generic[*T]):
    guard : Callable[[*T] , bool | None]
    _connections : Set[Connection[*T]]
    _tEvent : threading.Event
    _waiting : Dict[Thread , Tuple[*T] | Any | None]

    def __init__(self , guard : Callable[[*T] , bool | None] = lambda *args : True) -> None:
        self.guard = guard
        self._connections = set()
        self._tEvent = threading.Event()
        self._waiting = {}

    def __call__(self, *args : *T) -> bool:
        if not self.guard(*args) : return False
        
        for t , v in self._waiting.items():
            if v != False : continue
            self._waiting[t] = args if len(args) > 1 else args[0] if len(args) > 0 else None

        self._tEvent.set()
        self._tEvent.wait()
        self._tEvent.clear()

        for c in self._connections.copy() : threading.Thread(target = lambda: c(*args)).start()
        return True

    class Connection(Generic[*G]):
        call : Callable[[*G]]
        event : Event[*G]
        def __init__(self , event : Event[*G] , call : Callable[[*G]]) -> None:
            self.call = call
            self.event = event
            event._connections.add(self)

        def __call__(self , *args : *G) -> Any:
            return self.call(*args)
        
        def disconnect(self) -> Callable[[*G]]:
            self.event._connections.remove(self)
            return self.call
        
    def connect(self , call : Callable[[*T]]) -> Connection[*T]:
        return self.Connection(self , call)
    
    def once(self , call : Callable[[*T]]) -> Connection[*T]:
        con = self.Connection(self , call)
        call = con.call

        def f(*args : *T):
            con.disconnect()
            return call(*args)
        con.call = f
        
        return con
    
    def wait(self , timeout : int | None = None) -> tuple[*T] | Any:
        """
        Yield current thread until either timeout or an event, returning the arguments of the event call.
        """
        thread = threading.current_thread()
        self._waiting[thread] = False
        self._tEvent.wait((timeout / 1000) if timeout != None else None)
        
        args = self._waiting.pop(thread)
        return args


__all__ = ["Event"]