from typing import Callable, Coroutine, Dict, List

AsyncCallback = Callable[..., Coroutine]

class AsyncEventEmitter:
    listeners: Dict[str, List[AsyncCallback]] = {}

    def __init__(self) -> None:
        self.listeners = {}
