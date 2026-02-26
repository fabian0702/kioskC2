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

        self.tasks:list[asyncio.Task] = []

        self.handle_messages_task = asyncio.create_task(self.handle_messages())

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
            pending_result = PluginMessage(client_id=message.client_id, operation=message.operation, state="pending", id=message.id)
            await self.result_bucket.put(message.id, pending_result.model_dump_json().encode())
            await self.nc.publish(f"plugin.response.{self.client_id}")

            print(f"Running method {message.operation} for client {message.client_id} with args {message.args} and kwargs {message.kwargs}")

            result = await self.run_method(message)

            await self.result_bucket.put(message.id, result.model_dump_json().encode())
            await self.nc.publish(f"plugin.response.{self.client_id}")

        handle_message_task = asyncio.create_task(task_wrapper())
        self.tasks.append(handle_message_task)

        def done_callback(task: asyncio.Task):
            self.tasks.remove(task)
        
        handle_message_task.add_done_callback(done_callback)

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
        for task in self.tasks:
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