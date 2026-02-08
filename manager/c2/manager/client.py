import asyncio
import traceback

from asyncio import Future

from nats import NATS

from c2.manager.callback_manager import CallbackManager, TIMEOUT
from c2.manager.base import Message


class Client:
    def __init__(self, id:str, nc:NATS):
        self.id = id
        self.nc = nc
        self.js = nc.jetstream()
        self.cbm = CallbackManager()
        self.run_task = asyncio.create_task(self.run())

    def _done_callback(self, future:Future):
        exception = future.exception()
        if exception:
            traceback.print_exception(exception)

    async def timeout_callback(self, operation_id:str):
        print(f"Client {self.id} failed to respond within {TIMEOUT}s for operation with id {operation_id}")

        message = Message(id=operation_id, operation='timeout', data={'error': f'The client failed to respond within {TIMEOUT}s'})
        await self.nc.publish(f"manager.responses.{self.id}", message.model_dump_json().encode())

    async def reconnect_callback(self, operation_id:str):
        print(f"Client {self.id} reconnected, resending queued messages")

        message = Message(id=operation_id, operation='reconnection', data={'error': f'The client failed to respond within {TIMEOUT}s'})
        await self.nc.publish(f"manager.responses.{self.id}", message.model_dump_json().encode())

    async def wait_for_callback(self, operation_id:str):
        id = f"{self.id}.{operation_id}"

        await self.cbm.wait_for_callback(id, on_timeout=lambda: self.timeout_callback(id))

    async def handle_operations(self):
        try:
            manager_sub = await self.js.subscribe(f"manager.operations.{self.id}")
            
            async for msg in manager_sub.messages:
                msg.ack()
                try:
                    message = Message.model_validate_json(msg.data.decode())
                except Exception as e:
                    print(f"Failed to parse message for operation {self.id} with error {e}")
                    continue

                print(f"Received operation for client {self.id} with {repr(message)}")

                await self.wait_for_callback(message.id)

                await self.nc.publish(f"client.operations.{self.id}", message.model_dump_json().encode())
            
        except asyncio.CancelledError:
            await manager_sub.unsubscribe()

    async def handle_responses(self):
        try:
            reponse_sub = await self.nc.subscribe(f"client.responses.{self.id}")

            async for msg in reponse_sub.messages:
                try:
                    message = Message.model_validate_json(msg.data.decode())
                except Exception as e:
                    print(f"Failed to parse message for client {self.id} with error {e}")
                    continue

                print(f"Received response for client {self.id} with {repr(message)}")

                self.cbm.trigger_callback(f"{self.id}.{message.id}")

                await self.nc.publish(f"manager.responses.{self.id}", message.model_dump_json().encode())

        except asyncio.CancelledError:
            await reponse_sub.unsubscribe()

    async def run(self):
        try:
            operations_task = asyncio.create_task(self.handle_operations())
            response_task = asyncio.create_task(self.handle_responses())

            results = await asyncio.gather(operations_task, response_task)
        except asyncio.CancelledError:
            operations_task.cancel()
            response_task.cancel()

            results = await asyncio.gather(operations_task, response_task, return_exceptions=True)
            
        for result in results:
            if isinstance(result, Exception):
                traceback.print_exception(result)

        self.cbm.cleanup(on_cleanup=self.reconnect_callback)

    def terminate_client(self):
        self.run_task.cancel() 
        try:
            self.run_task.result()
        except Exception as e:
            traceback.print_exception(e)


class ClientManager:
    def __init__(self, nc:NATS):
        self.nc = nc
        self.clients: dict[str, Client] = {}

    def start_client(self, id:str) -> Client:
        new_client = Client(id, self.nc)
        self.clients[id] = new_client

    def remove_client(self, id:str):
        if not id in self.clients:
            print(f"Trying to remove nonexisting client with id {id}")
            return

        self.clients[id].terminate_client()
        del self.clients[id]

    def connect_client(self, id:str):
        if id in self.clients:
            self.remove_client(id)

        self.start_client(id)