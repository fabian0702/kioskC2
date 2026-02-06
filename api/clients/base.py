from fastapi.routing import APIRouter
from pydantic import BaseModel
from typing import ClassVar, Any

import inspect

from page.builder import add_js_plugin
import os

class Message(BaseModel):
    operation: str
    data: Any

client_router = APIRouter(prefix="/clients")

class Client:
    js_plugin: ClassVar[str]
    router: ClassVar[APIRouter]

    def __init__(self, id:str):
        self.id = id
        self.status = "connected"
        self.queued_requests: list[Message] = []

    async def prepare_response(self, data:dict) -> list[dict]:
        message = Message.model_validate(data)

        print(f"Preparing response for client {self.id} with message: {message}")

        response = await handle_message(message)

        responses = [response] + self.queued_requests
        self.queued_requests = []

        print(f"Prepared response for client {self.id}: {responses}")

        return [msg.model_dump() for msg in responses if msg is not None]
    
    def enqueue_message(self, message: Message):
        self.queued_requests.append(message)

    def update(self, *args, **kwargs):
        """Update the internal data if the client reconnects."""
        pass

class ClientManager:
    def __init__(self):
        self.clients: dict[str, Client] = {}

    def add_client(self, client: Client):
        if client.id in self.clients:
            return
        self.clients[client.id] = client

    def get_client(self, id:str, client_class=Client, args=(), kwargs={}) -> Client:
        if id not in self.clients:
            self.clients[id] = client_class(id, *args, **kwargs)
        else:
            self.clients[id].update(*args, **kwargs)
        return self.clients[id]
    
    def enqueue_message(self, client_id:str, message: Message):
        client = self.get_client(client_id)
        client.enqueue_message(message)

client_manager = ClientManager()

async def handle_message(message: Message) -> Message:
    match message.operation:
        case "heartbeat":
            if message.data != "ping":
                None
            return Message(operation="heartbeat", data="pong")
        case _:
            print(f"Unknown operation: {message.operation}")

def register_client(client_class: type[Client]):
    """Decorator to register a client class. The client class must inherit from Client and implement the required methods."""
    if not issubclass(client_class, Client):
        raise ValueError(f"Class {client_class.__name__} must be a subclass of Client")
    
    if not hasattr(client_class, "router"):
        raise ValueError(f"Class {client_class.__name__} must have a 'router' attribute of type APIRouter")
    
    if not hasattr(client_class, "js_plugin"):
        raise ValueError(f"Class {client_class.__name__} must have a 'js_plugin' attribute of type str")
    
    class_path = inspect.getfile(client_class)

    base_dir = os.path.dirname(os.path.abspath(class_path))
    js_plugin_path = os.path.join(base_dir, client_class.js_plugin)

    add_js_plugin(js_plugin_path)

    client_router.include_router(client_class.router)