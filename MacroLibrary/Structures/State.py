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

    def __call__(self) -> bool:
        v = self.value
        if self._get_ != None: v = self._get_(v)
        return v
    
    def _update(self , increment : T | None = None):
        value = self.value

        if not isinstance(increment , type(self.counter)):
            raise TypeError(f"arg must be {type(self.counter).__name__}, got {type(increment).__name__}")
        if isinstance(increment , bool):
            value = increment
        elif isinstance(increment , int):
            self.counter += increment
            value = self.counter > 0
        
        if value != self.value:
            self.value = value
            super().__call__(self())
        
        return True

__all__ = ["State"]