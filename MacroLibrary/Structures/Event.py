from .common import *
import inspect

T = TypeVarTuple("T")
G = TypeVarTuple("G")
P = ParamSpec("P")
class Event(Generic[P]):
    guard : Callable[P , bool | None]
    _callsig : inspect.Signature
    _connections : Set[Connection[P]]
    _tEvent : threading.Event
    _waiting : Dict[Thread , Any | None]

    def __init__(self , guard : Callable[P , bool | None] = lambda *args : True) -> None:
        self.guard = guard
        self._callsig = inspect.signature(guard)
        self._connections = set()
        self._tEvent = threading.Event()
        self._waiting = {}

    def __call__(self, *args : P.args , **kwargs : P.kwargs) -> bool:
        bound = self._callsig.bind_partial(*args , **kwargs); bound.apply_defaults()
        args = bound.args; kwargs = bound.kwargs
        if not self.guard(*args , **kwargs) : return False
        
        for t , v in self._waiting.items():
            if v != False : continue
            self._waiting[t] = None if len(args) == 0 else args[0] if len(args) == 1 else args

        self._tEvent.set()
        self._tEvent.wait()
        self._tEvent.clear()

        for c in self._connections.copy():
            threading.Thread(
                target=c.__call__,
                args=args,
                kwargs=kwargs,
            ).start()
        return True

    class Connection(Generic[P]):
        call : Callable[P]
        event : Event[P]
        def __init__(self , event : Event[P] , call : Callable[P]) -> None:
            call = truncateCall(event.guard , call)
            self.call = call
            self.event = event
            event._connections.add(self)

        def __call__(self , *args : P.args , **kwargs : P.kwargs) -> Any:
            return self.call(*args , **kwargs)
        
        def disconnect(self) -> Callable[P]:
            self.event._connections.remove(self)
            return self.call
        
    def connect(self , call : Callable[P]) -> Connection[P]:
        return self.Connection(self , call)
    
    def once(self , call : Callable[P]) -> Connection[P]:
        con = self.Connection(self , call)
        call = con.call

        def f(*args : P.args , **kwargs : P.kwargs):
            con.disconnect()
            return call(*args , **kwargs)
        con.call = f
        
        return con
    
    def wait(self , timeout : int | None = None) -> Any:
        """
        Yield current thread until either timeout or an event, returning the arguments of the event call.
        """
        thread = threading.current_thread()
        self._waiting[thread] = False
        self._tEvent.wait((timeout / 1000) if timeout != None else None)
        
        args = self._waiting.pop(thread)
        return args


__all__ = ["Event"]