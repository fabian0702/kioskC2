from fastapi import Request
from fastapi.routing import APIRouter
from pydantic import BaseModel
from typing import ClassVar, Any, Callable, Awaitable, Literal, Optional

import time
import asyncio
import inspect

import os

CLIENT_HEARTBEAT_INTERVAL = 2
CLIENT_HEARTBEAT_TIMEOUT = CLIENT_HEARTBEAT_INTERVAL * 5

class ClientRunMessage(BaseModel):
    operation: str
    data: Any
    id:str

async def run_callback(callback:Optional[Callable], *args, **kwargs):
    if not callback:
        return 
    
    result = callback(*args, **kwargs)

    if isinstance(result, Awaitable):
        await result

class Client:
    js_plugin: ClassVar[str]
    router: ClassVar[APIRouter]

    def __init__(self, id:str, manager: 'ClientManager'):
        self.id = id
        self.manager = manager
        self.status:Literal["connected", "disconnected"] = "connected"
        self.queued_requests: list[ClientRunMessage] = []
        self.last_heartbeat = time.time()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        client_manager.register_client(cls)

    def handle_heartbeat(self):
        self.status = 'connected'
        self.last_heartbeat = time.time()

    async def prepare_response(self, data:dict) -> list[dict]:
        message = ClientRunMessage.model_validate(data)

        print(f"Preparing response for client {self.id} with message: {message}")

        response = await self.manager.handle_message(self.id, message)

        responses = [response] + self.queued_requests
        self.queued_requests = []

        print(f"Prepared response for client {self.id}: {responses}")

        return [msg.model_dump() for msg in responses if msg is not None]
    
    def enqueue_message(self, message: ClientRunMessage):
        self.queued_requests.append(message)

    @classmethod
    def get_client(cls, request: Request):
        hostheader = request.headers.get("host")
        id, *_ = hostheader.split(".")
        return client_manager.get_client(id, client_class=cls)

class ClientManager:
    def __init__(self):
        self.on_msg_callback:Callable[[str, ClientRunMessage], None] = None
        self.on_disconnect_callback:Callable[[str], None] = None
        self.on_connect_callback:Callable[[str], None] = None
        self.clients: dict[str, Client] = {}
        self.router = APIRouter(prefix="/clients")

    async def track_heartbeats(self):
        while True:
            for id, client in self.clients.items():
                if time.time() - client.last_heartbeat < CLIENT_HEARTBEAT_TIMEOUT:
                    continue
                
                if client.status == 'connected':
                    await run_callback(self.on_disconnect_callback, id)

                client.status = 'disconnected'

            await asyncio.sleep(CLIENT_HEARTBEAT_INTERVAL)

    def on_msg(self, callback:Callable[[str, ClientRunMessage], None]):
        self.on_msg_callback = callback

    def on_disconnect(self, callback:Callable[[str], None]):
        self.on_disconnect_callback = callback

    def on_connect(self, callback:Callable[[str], None]):
        self.on_connect_callback = callback

    async def msg_call(self, id:str, msg:ClientRunMessage):
        print(f"ClientManager received message for client {id}: {msg}")

        await run_callback(self.on_msg_callback, id, msg)

    def add_client(self, client: Client):
        if client.id in self.clients:
            return
        self.clients[client.id] = client

    def get_client(self, id:str, client_class=Client, args=(), kwargs={}) -> Client:
        if 'manager' in inspect.signature(client_class).parameters:
            kwargs['manager'] = self
        if id not in self.clients:
            self.clients[id] = client_class(id, **kwargs)
        return self.clients[id]
    
    def enqueue_message(self, client_id:str, message: ClientRunMessage):
        client = self.get_client(client_id)
        client.enqueue_message(message)

    def handle_heartbeat(self, client_id:str, message: ClientRunMessage):
        if message.data != "ping":
            None
        
        client = self.get_client(client_id)
        client.handle_heartbeat()

        return ClientRunMessage(operation="heartbeat", data="pong", id=message.id)

    async def handle_message(self, client_id:str, message: ClientRunMessage) -> ClientRunMessage:
        match message.operation:
            case "heartbeat":
                return self.handle_heartbeat(client_id, message)
            case 'connect':
                await run_callback(self.on_connect_callback, client_id)
            case _:
                await self.msg_call(client_id, message)

    def register_client(self, client_class: type[Client]):
        """Decorator to register a client class. The client class must inherit from Client and implement the required methods."""
        if not issubclass(client_class, Client):
            raise ValueError(f"Class {client_class.__name__} must be a subclass of Client")
        
        if not hasattr(client_class, "router"):
            raise ValueError(f"Class {client_class.__name__} must have a 'router' attribute of type APIRouter")
        
        self.router.include_router(client_class.router)

client_manager = ClientManager()