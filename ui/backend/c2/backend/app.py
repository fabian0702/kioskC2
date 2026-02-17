import asyncio
import json

import socketio
import uvicorn
from nats.errors import TimeoutError as NATSTimeoutError

from c2.backend.classes import PluginMessage
from c2.backend.state import AppState


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

async def request_clients():
    clients = await state.client_kv.keys()
    await sio.emit('clients.response', clients)

@sio.on('clients.request')
async def get_clients(sid: str):
    if not state.client_kv:
        return
        
    await request_clients()

state.on_client_connect(request_clients)

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
    uvicorn.run(app=sio_app, host='0.0.0.0')