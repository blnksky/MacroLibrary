<<<<<<< HEAD
from .imports import *
from .types import *

exitEvent = threading.Event()

# temporal
def now() -> int:
    """Return current time in milliseconds."""
    return int(time.time() * 1000)

def sleep(dt : float = 0) -> None:
    """
    Yields code execution of current thread for dt milliseconds
    """
    time.sleep(dt / 1000)

def delay(callback = lambda : None , delay : int = 0):
        """
        Run callback after delay as millisecond integer.
        """
        delay = 0 if delay <= 0 else delay

        def wrapper():
            callback()

        if delay > 0 : thread = threading.Timer(interval = float(delay) / 1000 , function = wrapper)
        else: thread = threading.Thread(target = wrapper)
        thread.start()
        return thread

# structural
def path(obj : dict, path : str):
    """
    Access nested dict via dot notation.
    Example: path(data, "a.b.c")
    """
    current = obj

    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]

    return current

def bindInput(id : InputId , call : Callable) -> None:
    lambda:() #placeholder

def inputYield(id : InputId , call : Callable) -> None:
    if re.match("down" , id): lambda:() #placeholder
=======
from .imports import *
from .types import *

exitEvent = threading.Event()

# temporal
def now() -> int:
    """Return current time in milliseconds."""
    return int(time.time() * 1000)

def sleep(dt : float = 0) -> None:
    """
    Yields code execution of current thread for dt milliseconds
    """
    time.sleep(dt / 1000)

def delay(callback = lambda : None , delay : int = 0):
        """
        Run callback after delay as millisecond integer.
        """
        delay = 0 if delay <= 0 else delay

        def wrapper():
            callback()

        if delay > 0 : thread = threading.Timer(interval = float(delay) / 1000 , function = wrapper)
        else: thread = threading.Thread(target = wrapper)
        thread.start()
        return thread

# structural
def path(obj : dict, path : str):
    """
    Access nested dict via dot notation.
    Example: path(data, "a.b.c")
    """
    current = obj

    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]

    return current

def bindInput(id : InputId , call : Callable) -> None:
    lambda:() #placeholder

def inputYield(id : InputId , call : Callable) -> None:
    if re.match("down" , id): lambda:() #placeholder
>>>>>>> 22514187589849295d4fb64b5b37e78e37f7fa80
    else: lambda:() #placeholder