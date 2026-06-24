from ..common import *

def hashable(obj : Any | Iterable) -> bool:
    try: hash(obj); return True
    except TypeError: return False

def isStruct(obj : Iterable) -> bool:
    for i in obj:
        if not hashable(i): return False
    return True

def updateDict(f : dict , upd : dict):
    for i , e in upd.items():
        if f.get(i) != None and type(e) == type(f[i]):
            if isinstance(e , dict): updateDict(f[i] , e)
            elif isinstance(e , set): f[i] |= e
            else: f[i] = e
        else: f[i] = e
    return f
