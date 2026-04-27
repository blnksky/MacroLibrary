from .common import *
from .Event import Event

class State(Event[bool]):
    _state : int
    _buffer : int
    _threads : Set[Thread]
    _threadEvent : threading.Event
    _bufferQueue : List[Callable[[bool]]]

    def __init__(self , buffer : int = 0):
        super().__init__()
        self._state = 0
        self._buffer = buffer
        self._threadEvent = threading.Event()
        self._bufferQueue = list()

    def __call__(self, *args):
        return self._state > 0
    
    def update(self , increment : int = 0) -> bool:
        """
        Changes the state representative value by an increment
        value > 0 is the bool equivalent to the state
        """

        self._state += increment
        if self(): self._threadEvent.set()
        else: self._threadEvent.clear()
        super().__call__(self())
        if not self() : return False

        if len(self._bufferQueue) > 0 : delay(self._bufferQueue.pop(0) , self._buffer)
        return True
    
    def wait(self , timeout : int | None) -> bool:
        """
        Yields the current thread for timeout milliseconds until either state becomes true or timeout occurs, then returns current state.
        """


        if self() : return self()

        if timeout == None : timeout = self._buffer
        self._threadEvent.wait(timeout / 1000)

        return self()

    def queue(self , call : Callable) -> bool:
        if self._buffer <= 0 : return False

        self._bufferQueue.insert(0 , call)
        def callback():
            try: self._bufferQueue.remove(call)
            except: pass
        delay(callback , self._buffer)

        return True

__all__ = ["State"]
