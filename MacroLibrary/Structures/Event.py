from .common import *

P = ParamSpec("P")
G = ParamSpec("G")
class Event(Generic[P]):
    guard : Callable[P , bool]
    _connections : Set[Connection[P]]
    _tEvent : threading.Event
    _waiting : Dict[Thread , Tuple[Any , ...] | bool]

    def __init__(self , guard : Callable[P , bool] = lambda *args : True) -> None:
        self.guard = guard
        self._connections = set()
        self._tEvent = threading.Event()
        self._waiting = {}

    def __call__(self, *args : P.args , **kwargs : P.kwargs) -> bool:
        if not self.guard(*args , **kwargs) : return False
        
        for t , v in self._waiting.items():
            if v != False : continue
            self._waiting[t] = args

        self._tEvent.set()
        self._tEvent.wait()
        self._tEvent.clear()

        for c in self._connections.copy() : threading.Thread(target = lambda: c(*args , **kwargs)).start()
        return True

    class Connection(Generic[G]):
        call : Callable[G]
        event : Event[G]
        def __init__(self , event : Event[G] , call : Callable[G]) -> None:
            self.call = call
            self.event = event
            event._connections.add(self)

        def __call__(self , *args : G.args , **kwargs : G.kwargs) -> Any:
            return self.call(*args , **kwargs)
        
        def disconnect(self) -> Callable[G]:
            self.event._connections.remove(self)
            return self.call
        
    def connect(self , call : Callable[P]) -> Connection[P]:
        return self.Connection(self , call)
    
    def once(self , call : Callable[P]) -> Connection[P]:
        con = self.Connection(self , call)
        call = con.call

        def f(*args , **kwargs):
            con.disconnect()
            return call(*args , **kwargs)
        con.call = f
        
        return con
    
    def wait(self , timeout : int | None = None) -> Tuple[Any , ...] | Any | bool:
        """
        Yield current thread until either timeout or an event, returning the arguments of the event call.
        """
        thread = threading.current_thread()
        self._waiting[thread] = False
        self._tEvent.wait((timeout / 1000) if timeout != None else None)
        
        args = self._waiting.pop(thread)
        return args if not isinstance(args , tuple) or len(args) > 1 else args[0] if len(args) > 0 else None
    

__all__ = ["Event"]