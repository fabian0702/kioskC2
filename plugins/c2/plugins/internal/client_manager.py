import asyncio

from nats import NATS
from nats.js.kv import KeyValue

from c2.plugins.internal.classes import PluginMessage
from c2.plugins.internal.loader import Loader, MethodsDict
from c2.plugins.internal.utils import get_or_create_kv


class Client:
    def __init__(self, nc:NATS, methods: MethodsDict,  result_bucket: KeyValue, client_id:str):
        self.nc = nc
        self.js = nc.jetstream()
        self.client_id = client_id
        self.loaded_methods: MethodsDict = methods
        self.result_bucket = result_bucket

        self.tasks:dict[str, asyncio.Task] = {}
        # ids the operator deleted before/while the command was running - once a
        # message id lands here its result must never be (re)written, even if
        # the client answers late or the cancellation couldn't interrupt it.
        self.cancelled_ids:set[str] = set()

        self.handle_messages_task = asyncio.create_task(self.handle_messages())
        self.handle_cancellations_task = asyncio.create_task(self.handle_cancellations())

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
            plugin_instance = await plugin.new(self.nc, self.client_id)
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
            await self.result_bucket.put(message.id, pending_result.model_dump_json().encode())
            await self.nc.publish(f"plugin.response.{self.client_id}")

            print(f"Running method {message.operation} for client {message.client_id} with args {message.args} and kwargs {message.kwargs}")

            result = await self.run_method(message)

            if message.id in self.cancelled_ids:
                # Deleted while running (or while the cancellation was in
                # flight) - drop the result instead of resurrecting an entry
                # the operator already asked to get rid of.
                self.cancelled_ids.discard(message.id)
                return

            await self.result_bucket.put(message.id, result.model_dump_json().encode())
            await self.nc.publish(f"plugin.response.{self.client_id}")

        handle_message_task = asyncio.create_task(task_wrapper())
        self.tasks[message.id] = handle_message_task

        def done_callback(task: asyncio.Task):
            self.tasks.pop(message.id, None)

        handle_message_task.add_done_callback(done_callback)

    async def cancel_message(self, message_id: str):
        """Cancel a pending/running command so it never (re)appears in the result bucket."""
        self.cancelled_ids.add(message_id)

        try:
            await self.result_bucket.purge(message_id)
        except Exception:
            pass

        task = self.tasks.get(message_id)
        if task and not task.done():
            task.cancel()

    async def handle_cancellations(self):
        """Listens for delete requests from the UI so in-flight commands can be cancelled."""
        sub = await self.nc.subscribe(f"client.cancel.{self.client_id}")
        async for msg in sub.messages:
            await self.cancel_message(msg.data.decode())

    async def handle_messages(self):
        """Continuously handle incoming messages from the client."""
        js = self.nc.jetstream()

        sub = await js.subscribe(f"plugin.run.{self.client_id}")

        async for msg in sub.messages:
            await msg.ack()

            try:
                message = PluginMessage.model_validate_json(msg.data.decode())
            except Exception as e:
                print(f"Failed to parse message for client {self.client_id} with error {e}")
                continue

            await self.handle_message(message)

    async def teardown(self):
        """Cancel all running tasks for this client."""
        self.handle_cancellations_task.cancel()
        for task in self.tasks.values():
            task.cancel()


class ClientManager:
    def __init__(self, nc:NATS, loader:Loader):
        self.nc = nc
        self.loader = loader
        self.clients: dict[str, Client] = {}

    async def teardown_client(self, client_id:str):
        if not client_id in self.clients:
            print(f"Attempted to teardown client {client_id} which does not exist")
            return
        
        client = self.clients[client_id]
        await client.teardown()

        del self.clients[client_id]

    async def connect_client(self, client_id:str):
        if client_id in self.clients:
            print(f"Client {client_id} already exists, tearing down existing client before reconnecting")
            await self.teardown_client(client_id)

        result_bucket = await get_or_create_kv(self.nc.jetstream(), f"results_{client_id}")
        client = Client(self.nc, self.loader.methods, result_bucket, client_id)

        self.clients[client_id] = client

    async def run(self):
        sub = await self.nc.subscribe("client.connect")
        async for msg in sub.messages:
            client_id = msg.data.decode()
            print(f"Received connection message for client {client_id}")
            await self.connect_client(client_id)