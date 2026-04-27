from ..common import *
from ..Structures import *
from pynput import keyboard, mouse

active : Set[InputId] = set()

T = TypeVar("T" , bound = InputSig)
def normalize(i : T) -> T:
    if isinstance(i , tuple):
        l = list(i)
        for n in range(len(l)) : l[n] = normalize(l[n])
        i = tuple(l)
        return i

    for m in [" Down" , " Up" , "{" , "}" , "~" , "!" , "$" , "^" , "_l" , "_r"] : i = re.sub(m , "" , i)
    return i.lower()

def send(sig : InputSig):
    """
    Sends the input, either as a singular input char when 'sig' is an InputId, or an input combination represented by the reverse order of the tuple 'sig'
    """

    if not isinstance(sig , str):
        length = len(sig)
        for i in range(length) : send(sig[length - i] + " Down"); sleep()
        for i in range(length) : send(sig[i] + " Up"); sleep()
        return
    AHK.send_input("{" + sig + "}")
