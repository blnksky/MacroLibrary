from __future__ import annotations

import time
from threading import Thread
import threading
import queue
import re
import json
from typing import TypeVar , ParamSpec , Generic , Literal , Any , Callable , Optional , Set , Tuple , Dict , Mapping , List , overload , Final

from ahk import AHK as _initialize_ahk
AHK = _initialize_ahk()