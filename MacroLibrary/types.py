from .imports import *

type InputId = str
type InputSig = Tuple[InputId , ...] | InputId
type KeybindEntry = Tuple[InputSig , Callable[[InputId]]]