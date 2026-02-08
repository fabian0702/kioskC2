import traceback
import asyncio

from asyncio import Event, Future

from typing import Callable

TIMEOUT = 10


class CallbackManager:
    def __init__(self):
        self.callbacks: dict[str, Event] = {}

    def create_callback(self, id:str) -> Event:
        event = Event()
        self.callbacks[id] = event
        return event

    def trigger_callback(self, id:str):
        if not id in self.callbacks:
            print(f"Received callback for nonexisting id {id}")
            return

        if self.callbacks[id].is_set():
            print(f"Received callback for already expired operation with id {id}")

        self.callbacks[id].set()

    async def wait_for_callback(self, id:str, timeout:int=TIMEOUT, on_timeout:Callable[[str], None]=None):
        if not id in self.callbacks:
            self.create_callback(id)
        
        task = asyncio.create_task(self._wait_for_callback(id, timeout=timeout, on_timeout=on_timeout))
        task.add_done_callback(self._done_callback)
    
    def _done_callback(self, future:Future):
        exception = future.exception()
        if exception:
            traceback.print_exception(exception)

    async def _wait_for_callback(self, id:str, timeout:int=TIMEOUT, on_timeout:Callable[[str], None]=None):
        try:
            await asyncio.wait_for(self.callbacks[id].wait(), timeout=timeout)
        except asyncio.TimeoutError:
            print(f"Callback for id {id} timed out after {timeout}s")
            if on_timeout:
                await on_timeout(id)
        finally:
            del self.callbacks[id]

    async def cleanup(self, on_cleanup:Callable[[str], None]=None):
        for id in self.callbacks:
            print(f"Cleaning up callback for operation {id}")
            if on_cleanup:
                await on_cleanup(id)