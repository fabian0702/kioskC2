import nats
from nats.errors import TimeoutError as NatsTimeoutError

from hashlib import sha256

from pydantic import BaseModel, Field
from secrets import token_hex

class ReconnectionError(Exception):
    pass

class TimeoutError(Exception):
    pass

class JSExecutionError(Exception):
    pass

class ClientMessage(BaseModel):
    operation: str
    data: dict
    id:str = Field(default_factory=lambda : token_hex(16))

class Methods:
    def __init__(self, nc: nats.NATS, client_id: str):
        self.nc = nc
        self.js = nc.jetstream()
        self.client_id = client_id

    async def _wait_for_response(self, operation_id:str):
        print(f'Waiting for msg on client.response.{self.client_id}.{operation_id}')
        sub = await self.nc.subscribe(f"client.response.{self.client_id}.{operation_id}", max_msgs=1)
        try:
            response_msg = await sub.next_msg(timeout=10)
        except NatsTimeoutError:
            raise TimeoutError("Response timed out")
        response = ClientMessage.model_validate_json(response_msg.data.decode())
        return response.data
    
    async def serve(self, content:str | bytes, extension:str = ''):
        """
        Serves the content on the internal webserver
        
        :param content: The content which should be served
        :type content: str | bytes
        :param extension: sets the file extension if not empty
        :type extension: str
        :return: the path where the file is served
        :rtype: str
        """
        if isinstance(content, str):
            content = content.encode()

        hash = sha256(content).hexdigest()
        path = f'/plugins/{hash}'

        if extension:
            path += '.' + extension

        with open(path, 'wb') as f:
            f.write(content)

        return path

    async def _send_client_msg(self, msg:ClientMessage):
        await self.nc.publish(f"client.operations.{self.client_id}", msg.model_dump_json().encode())

    async def eval_js(self, code: str):
        """
        Executes arbitrary code on the client and returns it's result or a error
        
        :param code: the javascript code to execute
        :type code: str

        Raises JSExecutionError if there is a error in the js code.
        """

        msg = ClientMessage(operation="eval_js", data={"code": code})

        await self._send_client_msg(msg)

        response = await self._wait_for_response(msg.id)
        
        if response.get("error"):
            raise JSExecutionError(response["error"])
        
        return response.get("result")

    async def load_plugin(self, url: str):
        """
        Loads a javascript file from the given URL.
        
        :param url: The url to load the file from
        :type url: str
        """
        msg = ClientMessage(operation="load_plugin", data={"url": url})

        await self._send_client_msg(msg)

        await self._wait_for_response(msg.id)

    async def bundle_page(self, url: str) -> str:
        """
        Generates a bundled version of the page at the given URL
        
        :param self: Description
        :param url: The url of the website which should be bundled
        :type url: str
        :return: returns the bundled html as a string
        :rtype: str
        """

        msg = ClientMessage(operation="bundle", data={"url": url})
        page_name = await self.nc.request(f"bundler.fetch", msg.model_dump_json().encode(), timeout=20)

        print(f"Got page with name: {page_name}")

        object_store = await self.js.object_store("bundler")
        page_data = await object_store.get(page_name.data.decode())
        
        return page_data.data.decode()
    
    async def preview_page(self, url: str) -> bytes:
        """
        Generates a preview of the page at the given URL
        
        :param url: Description
        :type url: The url of the website
        :return: returns the screenshot as bytes
        :rtype: bytes
        """

        msg = ClientMessage(operation="preview", data={"url": url})
        screenshot_name = await self.nc.request(f"bundler.fetch", msg.model_dump_json().encode(), timeout=20)

        object_store = await self.js.object_store("bundler")
        screenshot_data = await object_store.get(screenshot_name.data.decode())
        
        return screenshot_data.data