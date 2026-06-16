from ..common import *

def updateDict(f : dict , upd : dict):
    for i , e in upd.items():
        if f.get(i) != None and type(e) == type(f[i]):
            if isinstance(e , dict): updateDict(f[i] , e)
            elif isinstance(e , set): f[i] |= e
            else: f[i] = e
        else: f[i] = e
    return f
