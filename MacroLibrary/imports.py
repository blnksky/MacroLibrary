from __future__ import annotations
import time , threading , queue , re , os
from threading import Thread
from typing import TypeVar , TypeVarTuple , ParamSpec , Generic , Literal , Any , Callable , Optional , Set , Tuple , Dict , Mapping , List , overload , Final , Iterable

from ahk import AHK as _initialize_ahk
AHK = _initialize_ahk()
