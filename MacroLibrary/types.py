<<<<<<< HEAD
from .imports import *

type InputId = str
type InputSig = Tuple[InputId , ...] | InputId
type KeybindEntry = Tuple[InputSig , Callable[[InputId]]]
type BuildData = Dict[str , bool | str | List[str]]
=======
from .imports import *

type InputId = str
type InputSig = Tuple[InputId , ...] | InputId
type KeybindEntry = Tuple[InputSig , Callable[[InputId]]]
type BuildData = Dict[str , bool | str | List[str]]
>>>>>>> 22514187589849295d4fb64b5b37e78e37f7fa80
