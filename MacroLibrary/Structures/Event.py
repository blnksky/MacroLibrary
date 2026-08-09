from .common import *
import inspect

P = ParamSpec("P")
class Event(Generic[P]):
    guard : Callable[P , bool | None]
    _callsig : inspect.Signature
    _connections : Set[Connection[P]]
    _synced : List[Connection[P]]
    _tEvent : threading.Event
    _buffer : Dict[Thread , Tuple[Any , ...] | None]

    def __init__(self , guard : Callable[P , bool | None] = lambda *args : True) -> None:
        self.guard = guard
        self._callsig = inspect.signature(guard)
        self._synced = []
        self._connections = set()
        self._tEvent = threading.Event()
        self._buffer = {}

    def __call__(self, *args : P.args , **kwargs : P.kwargs) -> bool:
        bound = self._callsig.bind_partial(*args , **kwargs); bound.apply_defaults()
        args = bound.args; kwargs = bound.kwargs
        if not self.guard(*args , **kwargs) : return False
        
        for t , v in self._buffer.items():
            if v != None : continue
            self._buffer[t] = args

        self._tEvent.set()
        self._tEvent.wait()
        self._tEvent.clear()

        for c in self._synced.copy(): c(*args , **kwargs)
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
            call = matchParams(event.guard , call)
            self.call = call
            self.event = event

        def __call__(self , *args : P.args , **kwargs : P.kwargs) -> Any:
            return self.call(*args , **kwargs)
        
        def disconnect(self) -> Callable[P]:
            if self in self.event._synced: self.event._synced.remove(self)
            if self in self.event._connections: self.event._connections.remove(self)
            return self.call

    def sync(self , call : Callable[P] , idx : int | None = None) -> Connection[P]:
        """
        Connects a synced callback of call to the event launch. The callback order is determined by the order in which the calls are added, modified by the optional idx.
        """

        con = self.Connection(self , call)
        if idx != None: self._synced.insert(idx , con)
        else: self._synced.append(con)
        return con
    
    def connect(self , call : Callable[P]) -> Connection[P]:
        """
        Connects a parallel callback of call to the event launch.
        """

        con = self.Connection(self , call)
        self._connections.add(con)
        return con
    
    def syncOnce(self , call : Callable[P]) -> Connection[P]:
            con = self.sync(call)
            call = con.call
    
            def f(*args : P.args , **kwargs : P.kwargs):
                con.disconnect()
                return call(*args , **kwargs)
            con.call = f
            
            return con

    def once(self , call : Callable[P]) -> Connection[P]:
        con = self.connect(call)
        call = con.call

        def f(*args : P.args , **kwargs : P.kwargs):
            con.disconnect()
            return call(*args , **kwargs)
        con.call = f
        
        return con

    def wait(self , timeout : int | None = None , value : Any | None = None) -> Any:
        """
        Yield current thread until either timeout or an event, returning the arguments of the event call or false on timeout. Returns true instead if specified value is received.
        """

        if value != None:
            t = now()
            v = None
            while v != value and (timeout == None or now() - t <= timeout): v = self.wait(None if timeout == None else timeout - (now() - t))
            return True
        
        thread = threading.current_thread()
        self._buffer[thread] = None
        if not self._tEvent.wait((timeout / 1000) if timeout != None else None): return False

        args = self._buffer.pop(thread)
        return None if args == None or len(args) == 0 else args[0] if len(args) == 1 else args


__all__ = ["Event"]