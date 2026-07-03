import asyncio

import httpx
import socketio

HUB_URL = "http://ui:8000"
NAMESPACE = "/internal/plugins"
BUNDLER_URL = "http://website-bundler:8000"


class PluginTransport:
    """
    Everything plugin code needs to reach the outside world:
    - a Socket.IO client connected to ui/backend's internal hub namespace,
      used for device command dispatch/responses and reporting results
    - an HTTP client for the website-bundler service
    """

    def __init__(self, token: str):
        self.sio = socketio.AsyncClient()
        self.bundler_http = httpx.AsyncClient(base_url=BUNDLER_URL)
        self._token = token
        self._pending: dict[str, asyncio.Future] = {}

        self.sio.on("device.response", self._on_device_response, namespace=NAMESPACE)

    async def connect(self):
        # depends_on only waits for the ui container to start, not for it to
        # actually be ready to accept connections - retry instead of letting
        # a cold-start race crash the whole process.
        while True:
            try:
                await self.sio.connect(HUB_URL, namespaces=[NAMESPACE], auth={"token": self._token})
                return
            except socketio.exceptions.ConnectionError as e:
                print(f"Failed to connect to hub, retrying in 2s: {e}")
                await asyncio.sleep(2)

    async def _on_device_response(self, payload: dict):
        message = payload.get("message") or {}
        msg_id = message.get("id")
        future = self._pending.pop(msg_id, None) if msg_id else None
        if future and not future.done():
            future.set_result(message)

    async def send_device_command(self, client_id: str, message: dict, timeout: float = 10) -> dict:
        """Sends a command to a specific kiosk device and awaits its response, keyed by message id."""
        msg_id = message["id"]
        future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future
        try:
            await self.sio.emit("device.command", {"client_id": client_id, "message": message}, namespace=NAMESPACE)
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(msg_id, None)

    async def emit_methods_updated(self, methods: dict):
        await self.sio.emit("methods.updated", methods, namespace=NAMESPACE)

    async def emit_plugin_result(self, result: dict):
        await self.sio.emit("plugin.result", result, namespace=NAMESPACE)
