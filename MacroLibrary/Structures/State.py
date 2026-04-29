from .common import *
from .Event import Event

class State(Event):
    value : int
    update : Event[int]
    buffer : int | None

    def __init__(self, buffer : int | None = None , call: Callable[..., bool] = lambda *args: True) -> None:
        super().__init__(call)
        self.value = 0
        self.update = Event(lambda i: self._update(i))
        self.buffer = buffer

    def __call__(self) -> bool:
        return self.value > 0
    
    def _update(self , increment : int = 0):
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
