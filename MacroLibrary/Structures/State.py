from .common import *
from .Event import Event

T = TypeVar("T" , int , bool)
class State(Event , Generic[T]):
    value : T
    update : Event[int]
    buffer : int | None
    _get : Callable[[bool] , bool] | None = None

    def __init__(self, guard: Callable[[T], bool] = lambda *args: True , get: Callable[[bool] , bool] | None = None , value : T = 0 , buffer : int | None = None) -> None:
        super().__init__(guard)
        self._get = get
        self.value = value
        self.update = Event(lambda i: self._update(i))
        self.buffer = buffer

    def __call__(self) -> bool:
        res = self.value > 0 if isinstance(self.value , int) else self.value
        if self._get != None: res = self._get(res)
        return res
    
    def _update(self , increment : T | None = None):
        if not isinstance(increment , type(self.value)):
            raise TypeError(f"arg must be {type(self.value).__name__}, got {type(increment).__name__}")
        if isinstance(increment , bool):
            self.value = increment
        elif isinstance(increment , int):
            self.value += increment
        super().__call__(self())
        return True

    def wait(self , timeout : int | None = None):
        waiting = True
        if timeout == None: timeout = self.buffer

        def f(): waiting = False
        if timeout != None: delay(f , timeout)

        r = False
        while waiting :
            r = super().wait()
            if r: break
        return r

__all__ = ["State"]