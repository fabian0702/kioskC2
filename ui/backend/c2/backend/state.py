import os
import time
from typing import Optional, Callable, Awaitable

import socketio

INTERNAL_HUB_TOKEN = os.environ["INTERNAL_HUB_TOKEN"]

PLUGINS_NAMESPACE = "/internal/plugins"
CLIENTS_NAMESPACE = "/internal/clients"


def _check_internal_auth(auth: Optional[dict]):
    if not isinstance(auth, dict) or auth.get("token") != INTERNAL_HUB_TOKEN:
        raise socketio.exceptions.ConnectionRefusedError("invalid internal hub token")


class AppState:
    """
    ui/backend is the hub: it's the only service other services connect to,
    and it's the sole owner of client/method/alias/result state (previously
    spread across NATS JetStream KV buckets shared between services).
    """

    def __init__(self, sio: socketio.AsyncServer):
        self.sio = sio

        self.clients: dict[str, dict] = {}
        self.aliases: dict[str, str] = {}
        self.methods: dict[str, dict] = {}
        self.results: dict[str, dict[str, dict]] = {}

        self.plugins_sid: Optional[str] = None
        self.clients_sid: Optional[str] = None

        self._on_client_connect_cb: Optional[Callable] = None
        self._on_client_disconnect_cb: Optional[Callable] = None
        self._on_plugin_loaded_cb: Optional[Callable] = None
        self._on_plugin_response_cb: Optional[Callable] = None

        self._register_internal_handlers()

    def on_client_connect(self, callback: Callable):
        self._on_client_connect_cb = callback

    def on_client_disconnect(self, callback: Callable):
        self._on_client_disconnect_cb = callback

    def on_plugin_loaded(self, callback: Callable):
        self._on_plugin_loaded_cb = callback

    def on_plugin_response(self, callback: Callable):
        self._on_plugin_response_cb = callback

    @staticmethod
    async def _run_callback(callback: Optional[Callable], *args):
        if not callback:
            return
        res = callback(*args)
        if isinstance(res, Awaitable):
            await res

    async def _relay(self, target_sid: Optional[str], namespace: str, event: str, data: dict):
        if not target_sid:
            return
        await self.sio.emit(event, data, namespace=namespace, to=target_sid)

    def is_plugins_ready(self) -> bool:
        return self.plugins_sid is not None

    async def dispatch_plugin_run(self, message: dict) -> bool:
        if not self.is_plugins_ready():
            return False
        await self.sio.emit("plugin.run", message, namespace=PLUGINS_NAMESPACE, to=self.plugins_sid)
        return True

    async def send_cancel(self, client_id: str, result_id: str):
        await self._relay(self.plugins_sid, PLUGINS_NAMESPACE, "cancel", {"client_id": client_id, "result_id": result_id})

    def get_clients(self) -> dict:
        clients = {}
        for client_id, info in self.clients.items():
            clients[client_id] = {**info, "alias": self.aliases.get(client_id)}
        return clients

    def get_results(self, client_id: str) -> list:
        return list(self.results.get(client_id, {}).values())

    def get_alias(self, client_id: str) -> Optional[str]:
        return self.aliases.get(client_id)

    def set_alias(self, client_id: str, alias: str):
        alias = alias.strip()
        if alias:
            self.aliases[client_id] = alias
        else:
            self.aliases.pop(client_id, None)

    def remove_client(self, client_id: str):
        self.clients.pop(client_id, None)
        self.aliases.pop(client_id, None)
        self.results.pop(client_id, None)

    def purge_result(self, client_id: str, result_id: str):
        self.results.get(client_id, {}).pop(result_id, None)

    def clear_results(self, client_id: str) -> list:
        """Clears and returns the ids that were cleared, so callers can notify plugins to cancel them."""
        ids = list(self.results.get(client_id, {}).keys())
        self.results.pop(client_id, None)
        return ids

    def _register_internal_handlers(self):
        # --- /internal/plugins: the plugins service connects here ---
        async def plugins_connect(sid, environ, auth=None):
            _check_internal_auth(auth)
            self.plugins_sid = sid

        def plugins_disconnect(sid):
            if self.plugins_sid == sid:
                self.plugins_sid = None

        async def methods_updated(sid, methods: dict):
            self.methods = methods
            await self._run_callback(self._on_plugin_loaded_cb)

        async def plugin_result(sid, result: dict):
            client_id = result.get("client_id")
            result_id = result.get("id")
            if not client_id or not result_id:
                return
            self.results.setdefault(client_id, {})[result_id] = result
            await self._run_callback(self._on_plugin_response_cb, client_id)

        async def device_command_from_plugins(sid, message: dict):
            await self._relay(self.clients_sid, CLIENTS_NAMESPACE, "device.command", message)

        self.sio.on("connect", plugins_connect, namespace=PLUGINS_NAMESPACE)
        self.sio.on("disconnect", plugins_disconnect, namespace=PLUGINS_NAMESPACE)
        self.sio.on("methods.updated", methods_updated, namespace=PLUGINS_NAMESPACE)
        self.sio.on("plugin.result", plugin_result, namespace=PLUGINS_NAMESPACE)
        self.sio.on("device.command", device_command_from_plugins, namespace=PLUGINS_NAMESPACE)

        # --- /internal/clients: the kiosk-facing "clients" service connects here ---
        async def clients_connect(sid, environ, auth=None):
            _check_internal_auth(auth)
            self.clients_sid = sid

        def clients_disconnect(sid):
            if self.clients_sid == sid:
                self.clients_sid = None

        async def client_connect(sid, data: dict):
            client_id = data.get("client_id")
            if not client_id:
                return
            self.clients[client_id] = {
                "status": "connected",
                "last_seen": time.time(),
                "user_agent": data.get("user_agent"),
            }
            # plugins needs to know too, so it can spin up a per-client command handler
            await self._relay(self.plugins_sid, PLUGINS_NAMESPACE, "client.connect", data)
            await self._run_callback(self._on_client_connect_cb)

        async def client_disconnect(sid, data: dict):
            client_id = data.get("client_id")
            entry = self.clients.get(client_id) if client_id else None
            if entry is not None:
                entry["status"] = "disconnected"
                entry["last_seen"] = data.get("last_seen", time.time())
            await self._run_callback(self._on_client_disconnect_cb)

        def client_heartbeat(sid, data: dict):
            client_id = data.get("client_id")
            if not client_id:
                return
            entry = self.clients.setdefault(client_id, {})
            entry["status"] = "connected"
            entry["last_seen"] = data.get("last_seen", time.time())
            entry["user_agent"] = data.get("user_agent")

        async def device_response(sid, message: dict):
            await self._relay(self.plugins_sid, PLUGINS_NAMESPACE, "device.response", message)

        self.sio.on("connect", clients_connect, namespace=CLIENTS_NAMESPACE)
        self.sio.on("disconnect", clients_disconnect, namespace=CLIENTS_NAMESPACE)
        self.sio.on("client.connect", client_connect, namespace=CLIENTS_NAMESPACE)
        self.sio.on("client.disconnect", client_disconnect, namespace=CLIENTS_NAMESPACE)
        self.sio.on("client.heartbeat", client_heartbeat, namespace=CLIENTS_NAMESPACE)
        self.sio.on("device.response", device_response, namespace=CLIENTS_NAMESPACE)
