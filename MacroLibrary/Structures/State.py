from .common import *
from .Event import Event

T = TypeVar("T" , int , bool)
class State(Event[bool] , Generic[T]):
    value : T
    update : Event[int]
    buffer : int | None
    _prevState_ : bool
    _get_ : Callable[[bool] , bool] | None = None

    def __init__(self, guard: Callable[[bool], bool] = lambda *args: True , get: Callable[[bool] , bool] | None = None , value : T = 0 , buffer : int | None = None) -> None:
        super().__init__(guard)
        self.value = value
        self.update = Event(lambda i: self._update(i))
        self.buffer = buffer
        self._prevState_ = False
        self._get_ = get

    def __call__(self) -> bool:
        res = self.value > 0 if isinstance(self.value , int) else self.value
        if self._get_ != None: res = self._get_(res)
        return res
    
    def _update(self , increment : T | None = None):
        if not isinstance(increment , type(self.value)):
            raise TypeError(f"arg must be {type(self.value).__name__}, got {type(increment).__name__}")
        if isinstance(increment , bool):
            self.value = increment
        elif isinstance(increment , int):
            self.value += increment
        
        if self() != self._prevState_:
            self._prevState_ = self()
            super().__call__(self())
            
        return True

__all__ = ["State"]