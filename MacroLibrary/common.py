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
    if dt <= 0: return
    time.sleep(dt / 1000)

def delay(callback = lambda : None , delay : float = 0):
        """
        Run callback after delay as millisecond integer.
        """
        delay = 0 if delay <= 0 else delay

        def wrapper():
            callback()

        if delay > 0 : thread = threading.Timer(interval = delay / 1000 , function = wrapper)
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
    else: lambda:() #placeholder

# truncateCall
import functools
import inspect
from typing import Callable

def truncateCall(base: Callable, call: Callable) -> Callable:
    base_sig = inspect.signature(base)
    call_sig = inspect.signature(call)

    call_params = list(call_sig.parameters.values())

    @functools.wraps(call)
    def wrapper(*args, **kwargs):
        bound = base_sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()

        available = list(bound.arguments.values())
        used_positions = set()

        out_args = []
        out_kwargs = {}

        for param in call_params:
            # Skip variadic handling for now
            if param.kind is inspect.Parameter.VAR_POSITIONAL:
                for i, value in enumerate(available):
                    if i not in used_positions:
                        out_args.append(value)
                continue

            if param.kind is inspect.Parameter.VAR_KEYWORD:
                for key, value in bound.arguments.items():
                    if key not in call_sig.parameters:
                        out_kwargs[key] = value
                continue

            # 1. Prefer name matching
            if param.name in bound.arguments:
                value = bound.arguments[param.name]
                try:
                    used_positions.add(available.index(value))
                except ValueError:
                    pass

            # 2. Fall back to positional order
            else:
                value = None
                found = False

                for i, candidate in enumerate(available):
                    if i not in used_positions:
                        value = candidate
                        used_positions.add(i)
                        found = True
                        break

                if not found:
                    continue

            if param.kind is inspect.Parameter.KEYWORD_ONLY:
                out_kwargs[param.name] = value
            else:
                out_args.append(value)

        return call(*out_args, **out_kwargs)

    return wrapper