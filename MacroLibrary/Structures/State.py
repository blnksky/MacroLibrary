from .common import *
from .Event import Event

T = TypeVar("T" , int , bool)
class State(Event[bool] , Generic[T]):
    value : bool
    counter : int
    update : Event[int]
    buffer : int | None
    _prevState_ : bool
    _get_ : Callable[[bool] , bool] | None = None

    def __init__(self, guard: Callable[[bool], bool] = lambda *args: True , get: Callable[[bool] , bool] | None = None , value : T = 0 , buffer : int | None = None) -> None:
        super().__init__(guard)
        self.value = False
        self.counter = 0
        self.update = Event(lambda i: self._update(i))
        self.buffer = buffer
        self._get_ = get
        self._prevState_ = self()
        self.update(value)

    def __call__(self) -> bool: return self.value
    
    def _update(self , increment : T | None = None):
        value = self.value

        if not isinstance(increment , type(self.counter)):
            raise TypeError(f"arg must be {type(self.counter).__name__}, got {type(increment).__name__}")
        if isinstance(increment , bool):
            value = increment
        elif isinstance(increment , int):
            self.counter += increment
            value = self.counter > 0
        if self._get_ != None: value = self._get_(value)
        
        if value != self.value:
            self.value = value
            super().__call__(self())
        
        return True

    def wait(self , timeout : int | None = None , value : bool | None = None) -> Any:
        """
        Yield current thread until either timeout or positive state change / the specified value is reached. Returns false on timeout
        """

        if value != None and self() == value: return True
        return super().wait(timeout , value)

    def __enter__(self):
        if not self.wait(self.buffer , False): raise TimeoutError()
        self.update(True if isinstance(self.value , bool) else 1)
        return self

    def __exit__(self , exc_type, exc_value, traceback):
        self.update(False if isinstance(self.value , bool) else -1)


__all__ = ["State"]