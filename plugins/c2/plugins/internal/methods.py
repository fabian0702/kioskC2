import asyncio
import nats

from pydantic import BaseModel, Field
from secrets import token_hex

class ReconnectionError(Exception):
    pass

class TimeoutError(Exception):
    pass

class JSExecutionError(Exception):
    pass

class Message(BaseModel):
    operation: str
    data: dict
    id:str = Field(default_factory=lambda : token_hex(16))

class Methods:
    def __init__(self, nc: nats.NATS, client_id: str):
        self.nc = nc
        self.js = nc.jetstream()
        self.client_id = client_id

    async def _wait_for_response(self, operation_id:str):
        sub = await self.nc.subscribe(f"manager.responses.{self.client_id}.{operation_id}", max_msgs=1)
        response_msg = await sub.next_msg(timeout=10)
        response = Message.model_validate_json(response_msg.data.decode())
        match response.operation:
            case "reconnection":
                raise ReconnectionError(response.data.get('error'))
            case "timeout":
                raise TimeoutError(response.data.get('error'))
            case _:
                return response.data

    async def eval_js(self, code: str):
        msg = Message(operation="eval_js", data={"code": code})
        await self.js.publish(f"manager.operations.{self.client_id}", msg.model_dump_json().encode())
        
        response = await self._wait_for_response(msg.id)
        
        if response.get("error"):
            raise JSExecutionError(response["error"])
        
        return response.get("result")

    async def load_plugin(self, url: str):
        """Loads a javascript file from the given URL."""
        msg = Message(operation="load_plugin", data={"url": url})
        await self.js.publish(f"manager.operations.{self.client_id}", msg.model_dump_json().encode())
        
        await self._wait_for_response(msg.id)

    async def bundle_page(self, url: str) -> str:
        """Generates a bundled version of the page at the given URL and returns the html content as a string."""

        msg = Message(operation="bundle", data={"url": url})
        page_name = await self.nc.request(f"bundler.fetch", msg.model_dump_json().encode())

        object_store = await self.js.object_store("bundler")
        page_data = await object_store.get(page_name.data.decode())
        
        return page_data.data.decode()
    
    async def preview_page(self, url: str) -> bytes:
        """Generates a preview of the page at the given URL and returns the screenshot as bytes."""

        msg = Message(operation="preview", data={"url": url})
        screenshot_name = await self.nc.request(f"bundler.fetch", msg.model_dump_json().encode())

        object_store = await self.js.object_store("bundler")
        screenshot_data = await object_store.get(screenshot_name.data.decode())
        
        return screenshot_data.data