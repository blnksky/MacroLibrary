from ..common import *
from ..Structures import *
from pynput import keyboard, mouse
from collections import deque

active : Set[InputId] = set()
sent = deque(maxlen = 5)

T = TypeVar("T" , bound = InputSig)
def normalize(i : T) -> T:
    if isinstance(i , tuple):
        l = list(i)
        for n in range(len(l)) : l[n] = normalize(l[n])
        i = tuple(l)
        return i
    
    i = i.lower()
    i = re.sub(r" down| up|{|}|~|!|$|^" , "" , str(i)) # _l|_r
    
    return i

def sendEvent(sig : InputSig):
    """
    Sends the input, either as a singular input char when 'sig' is an InputId, or an input combination represented by the reverse order of the tuple 'sig'
    """

    if not isinstance(sig , str):
        length = len(sig)
        for i in range(length) : sendEvent(sig[length - i] + " Down"); sleep()
        for i in range(length) : sendEvent(sig[i] + " Up"); sleep()
        return
    
    AHK.send_input("{" + sig + "}")


def send(sig : InputSig):
    """
    Sends the input as virtual input, either as a singular input char when 'sig' is an InputId, or an input combination represented by the reverse order of the tuple 'sig'
    """

    if not isinstance(sig , str):
        length = len(sig)
        for i in range(length) : send(sig[length - i] + " Down"); sleep()
        for i in range(length) : send(sig[i] + " Up"); sleep()
        return
    
    nsig = normalize(sig)
    sent.append(nsig)
    if re.search(r"up|down" , sig) == None: sent.append(nsig)
    sendEvent(sig)
