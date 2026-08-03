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

        # Flatten the bound arguments into positional and named forms.
        positional = []
        named = {}

        for name, param in base_sig.parameters.items():
            if name not in bound.arguments:
                continue

            value = bound.arguments[name]

            match param.kind:
                case inspect.Parameter.POSITIONAL_ONLY:
                    positional.append(value)

                case inspect.Parameter.POSITIONAL_OR_KEYWORD:
                    positional.append(value)
                    named[name] = value

                case inspect.Parameter.KEYWORD_ONLY:
                    named[name] = value

                case inspect.Parameter.VAR_POSITIONAL:
                    positional.extend(value)

                case inspect.Parameter.VAR_KEYWORD:
                    named.update(value)

        pos = 0
        out_args = []
        out_kwargs = {}

        for param in call_params:
            match param.kind:
                case inspect.Parameter.POSITIONAL_ONLY:
                    if pos < len(positional):
                        out_args.append(positional[pos])
                        pos += 1

                case inspect.Parameter.POSITIONAL_OR_KEYWORD:
                    if param.name in named:
                        out_args.append(named[param.name])
                    elif pos < len(positional):
                        out_args.append(positional[pos])
                        pos += 1

                case inspect.Parameter.KEYWORD_ONLY:
                    if param.name in named:
                        out_kwargs[param.name] = named[param.name]

                case inspect.Parameter.VAR_POSITIONAL:
                    out_args.extend(positional[pos:])
                    pos = len(positional)

                case inspect.Parameter.VAR_KEYWORD:
                    for k, v in named.items():
                        if k not in call_sig.parameters:
                            out_kwargs[k] = v

        return call(*out_args, **out_kwargs)

    return wrapper
