import asyncio
import json

from secrets import token_hex
from typing import Any, Dict, List, Optional, Union

import socketio
import uvicorn
import nats

from nats.aio.client import Client as NATSClient
from nats.js.client import JetStreamContext
from nats.js.kv import KeyValue
from nats.js.api import KeyValueConfig
from nats.js.errors import BucketNotFoundError
from nats.errors import TimeoutError as NATSTimeoutError

from pydantic import BaseModel, Field


NATS_URL = "nats://localhost:4222"

Argument = Union[str, int, float, bool]

class PluginMessage(BaseModel):
    client_id: str
    id: str = Field(default_factory=lambda: token_hex(16))
    operation: str
    data: Optional[Any] = None
    args: List[Argument] = []
    kwargs: Dict[str, Argument] = {}

class AppState:
    """
    Encapsulates the application state to ensure type safety 
    and avoid global variables.
    """
    def __init__(self):
        self.nc: Optional[NATSClient] = None
        self.js: Optional[JetStreamContext] = None
        self.method_kv: Optional[KeyValue] = None
        self.client_kv: Optional[KeyValue] = None

    async def startup(self):
        print(f"Connecting to NATS at {NATS_URL}...")
        self.nc = await nats.connect(NATS_URL)
        self.js = self.nc.jetstream()
        
        self.method_kv = await self._get_or_create_kv('methods')
        self.client_kv = await self._get_or_create_kv('clients')
        print("Startup complete")

    async def shutdown(self):
        if self.nc:
            await self.nc.drain()
            await self.nc.close()
            print("Shutdown complete")
    
    async def _get_or_create_kv(self, bucket_name: str) -> KeyValue:
        """Internal helper to fetch or create a KV bucket."""
        if not self.js:
            raise RuntimeError("JetStream context not initialized")

        try:
            return await self.js.key_value(bucket_name)
        except BucketNotFoundError:
            print(f"Bucket '{bucket_name}' not found. Creating...")
            config = KeyValueConfig(bucket=bucket_name, history=5)
            return await self.js.create_key_value(config)


state = AppState()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(sio, on_startup=state.startup, on_shutdown=state.shutdown)


async def plugin_respond(client_id: str, request_id: str):
    """
    Background task: Subscribes to a specific NATS subject, 
    waits for a single response, and emits it via Socket.IO.
    """
    if not state.nc:
        return

    subject = f"plugin.response.{client_id}.{request_id}"
    
    try:
        sub = await state.nc.subscribe(subject, max_msgs=1)
        msg = await sub.next_msg(timeout=30)
        
        data = msg.data.decode()
        await sio.emit('plugin.response', data)

    except NATSTimeoutError:
        error_msg = {'id': request_id, 'error': 'Plugin response timed out'}
        await sio.emit('plugin.error', error_msg)
    except Exception as e:
        print(f"Error in plugin_respond: {e}")


@sio.on('clients.request')
async def get_clients(sid: str):
    if not state.client_kv:
        return
        
    clients = await state.client_kv.keys()
    await sio.emit('clients.response', clients)

@sio.on('methods.request')
async def get_methods(sid: str):
    if not state.method_kv:
        return

    method_names = await state.method_kv.keys()
    methods = {}

    for name in method_names:
        entry = await state.method_kv.get(name)
        if entry.value:
            methods[name] = json.loads(entry.value)

    await sio.emit('methods.response', methods)

@sio.on('plugin.run')
async def run_plugin(sid: str, plugin_args: dict):
    if not state.js:
        return {'status': 'error', 'message': "Server not ready"}

    try:
        message = PluginMessage.model_validate(plugin_args)

        topic = f"plugin.run.{message.client_id}"
        await state.js.publish(topic, message.model_dump_json().encode())

        asyncio.create_task(plugin_respond(message.client_id, message.id))

        return message.id

    except ValueError as e:
        return {'status': 'error', 'message': f"Invalid arguments: {str(e)}"}
    except Exception as e:
        print(f"Error running plugin: {e}")
        return {'status': 'error', 'message': "Internal server error"}


if __name__ == '__main__':
    uvicorn.run(app=sio_app)