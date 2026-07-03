import asyncio

from c2.plugins.internal.classes import PluginMessage
from c2.plugins.internal.loader import Loader, MethodsDict
from c2.plugins.internal.transport import PluginTransport, NAMESPACE
from c2.plugins.internal.utils import short


class Client:
    def __init__(self, transport:PluginTransport, methods: MethodsDict, client_id:str):
        self.transport = transport
        self.client_id = client_id
        self.loaded_methods: MethodsDict = methods

        self.tasks:dict[str, asyncio.Task] = {}
        # ids the operator deleted before/while the command was running - once a
        # message id lands here its result must never be (re)written, even if
        # the client answers late or the cancellation couldn't interrupt it.
        self.cancelled_ids:set[str] = set()

    async def run_method(self, message: PluginMessage):
        """Handle an incoming message from the client."""
        if not message.operation in self.loaded_methods:
            return PluginMessage(
                client_id=message.client_id,
                operation=message.operation,
                state="error",
                data=f"Unknown operation: {message.operation}",
                id=message.id
            )

        method, plugin, params = self.loaded_methods[message.operation]

        try:
            plugin_instance = await plugin.new(self.transport, self.client_id)
            result = await method(plugin_instance, *message.args, **message.kwargs)
            return PluginMessage(
                client_id=message.client_id,
                operation=message.operation,
                state="complete",
                data=result,
                id=message.id
            )
        except asyncio.CancelledError:
            return PluginMessage(
                client_id=message.client_id,
                operation=message.operation,
                state="error",
                data={},
                id=message.id
            )
        except Exception as e:
            return PluginMessage(
                client_id=message.client_id,
                operation=message.operation,
                state="error",
                data=str(e),
                id=message.id
            )

    async def handle_message(self, message: PluginMessage):
        """Handle an incoming message from the client."""
        async def task_wrapper():
            if message.id in self.cancelled_ids:
                self.cancelled_ids.discard(message.id)
                return

            pending_result = PluginMessage(client_id=message.client_id, operation=message.operation, state="pending", id=message.id)
            await self.transport.emit_plugin_result(pending_result.model_dump(mode="json"))

            print(f"Running method {message.operation} for client {message.client_id} with args {short(message.args)} and kwargs {short(message.kwargs)}")

            result = await self.run_method(message)

            if message.id in self.cancelled_ids:
                # Deleted while running (or while the cancellation was in
                # flight) - drop the result instead of resurrecting an entry
                # the operator already asked to get rid of.
                self.cancelled_ids.discard(message.id)
                return

            await self.transport.emit_plugin_result(result.model_dump(mode="json"))

        handle_message_task = asyncio.create_task(task_wrapper())
        self.tasks[message.id] = handle_message_task

        def done_callback(task: asyncio.Task):
            self.tasks.pop(message.id, None)

        handle_message_task.add_done_callback(done_callback)

    def cancel_message(self, message_id: str):
        """Cancel a pending/running command so it never (re)appears in the result bucket."""
        self.cancelled_ids.add(message_id)

        task = self.tasks.get(message_id)
        if task and not task.done():
            task.cancel()

    def teardown(self):
        """Cancel all running tasks for this client."""
        for task in self.tasks.values():
            task.cancel()


class ClientManager:
    def __init__(self, transport:PluginTransport, loader:Loader):
        self.transport = transport
        self.loader = loader
        self.clients: dict[str, Client] = {}

        transport.sio.on("client.connect", self._on_client_connect, namespace=NAMESPACE)
        transport.sio.on("plugin.run", self._on_plugin_run, namespace=NAMESPACE)
        transport.sio.on("cancel", self._on_cancel, namespace=NAMESPACE)

    def teardown_client(self, client_id:str):
        if not client_id in self.clients:
            print(f"Attempted to teardown client {client_id} which does not exist")
            return

        self.clients[client_id].teardown()
        del self.clients[client_id]

    def connect_client(self, client_id:str):
        if client_id in self.clients:
            print(f"Client {client_id} already exists, tearing down existing client before reconnecting")
            self.teardown_client(client_id)

        self.clients[client_id] = Client(self.transport, self.loader.methods, client_id)

    async def _on_client_connect(self, data: dict):
        client_id = data.get("client_id")
        if not client_id:
            return
        print(f"Received connection message for client {client_id}")
        self.connect_client(client_id)

    async def _on_plugin_run(self, message: dict):
        client_id = message.get("client_id")
        if not client_id:
            return

        try:
            parsed_message = PluginMessage.model_validate(message)
        except Exception as e:
            print(f"Failed to parse plugin.run message for client {client_id} with error {e}")
            return

        client = self.clients.get(client_id)
        if client is None:
            # Only NATS's durable stream used to guarantee a Client existed
            # by the time a command arrived; there's no equivalent replay
            # now, so register the client lazily instead of dropping the
            # command (e.g. plugins restarted after the device connected).
            self.connect_client(client_id)
            client = self.clients[client_id]

        await client.handle_message(parsed_message)

    async def _on_cancel(self, data: dict):
        client_id = data.get("client_id")
        result_id = data.get("result_id")
        if not client_id or not result_id:
            return

        client = self.clients.get(client_id)
        if client:
            client.cancel_message(result_id)
