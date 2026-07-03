import asyncio
import json

import socketio
import uvicorn
from nats.errors import TimeoutError as NATSTimeoutError
from nats.js.errors import NoKeysError

from c2.backend.classes import PluginMessage
from c2.backend.state import AppState


static_files = {
    '/': '/frontend/',
}

state = AppState()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(sio, on_startup=state.startup, on_shutdown=state.shutdown, static_files=static_files)


async def plugin_response(client_id: str):
    """
    Background task: Subscribes to a specific NATS subject and emits it via Socket.IO.
    """
    if not state.nc:
        return
    
    await sio.emit(f'plugin.response.{client_id}')

state.on_plugin_response(plugin_response)

async def request_clients():
    print("Requesting clients...")
    try:
        keys = await state.client_kv.keys()
    except NoKeysError:
        keys = []

    clients = {}
    for key in keys:
        entry = await state.client_kv.get(key)
        raw = entry.value.decode() if entry.value else ""
        try:
            info = json.loads(raw)
            if not isinstance(info, dict):
                info = {"status": raw}
        except ValueError:
            info = {"status": raw}

        info["alias"] = await state.get_alias(key)
        clients[key] = info

    await sio.emit('clients.response', clients)

@sio.on('results.request')
async def request_results(sid:str, client_id:str):
    if not state.js:
        return

    try:
        result_bucket = await state.get_or_create_kv(f"results_{client_id}")
        results = []
        try:
            keys = await result_bucket.keys()
        except NoKeysError:
            keys = []
        for key in keys:
            entry = await result_bucket.get(key)
            if entry.value:
                results.append(json.loads(entry.value))
        await sio.emit(f'results.response.{client_id}', json.dumps(results))
    except Exception as e:
        print(f"Error requesting results for client {client_id}: {e}")

@sio.on('clients.request')
async def get_clients(sid: str):
    if not state.client_kv:
        return
        
    await request_clients()

state.on_client_connect(request_clients)
state.on_client_disconnect(request_clients)


async def request_methods():
    if not state.method_kv:
        return

    print("Requesting methods...")

    try:
        method_names = await state.method_kv.keys()
    except NoKeysError:
        await sio.emit('methods.response', {})
        return

    methods = {}

    for name in method_names:
        entry = await state.method_kv.get(name)
        if entry.value:
            methods[name] = json.loads(entry.value)

    await sio.emit('methods.response', methods)

state.on_plugin_loaded(request_methods)

@sio.on('methods.request')
async def get_methods(sid: str):
    await request_methods()

@sio.on('client.remove')
async def remove_client(sid: str, client_id: str):
    await state.remove_client(client_id)
    await request_clients()

@sio.on('client.rename')
async def rename_client(sid: str, data: dict):
    client_id = data.get('client_id')
    alias = data.get('alias', '')
    if not client_id:
        return
    await state.set_alias(client_id, alias)
    await request_clients()

@sio.on('result.delete')
async def delete_result(sid: str, data: dict):
    client_id = data.get('client_id')
    result_id  = data.get('result_id')
    if not client_id or not result_id:
        return
    try:
        result_bucket = await state.get_or_create_kv(f"results_{client_id}")
        await result_bucket.purge(result_id)
        # Tell the plugins service so it cancels the command if it's still
        # running and never writes its result back, even if the client
        # answers after we've already purged it here.
        await state.nc.publish(f"client.cancel.{client_id}", result_id.encode())
    except Exception as e:
        print(f"Error deleting result {result_id} for client {client_id}: {e}")

@sio.on('results.clear')
async def clear_results(sid: str, client_id: str):
    if not client_id:
        return
    try:
        result_bucket = await state.get_or_create_kv(f"results_{client_id}")
        try:
            keys = await result_bucket.keys()
        except NoKeysError:
            keys = []
        for key in keys:
            await result_bucket.purge(key)
            await state.nc.publish(f"client.cancel.{client_id}", key.encode())
    except Exception as e:
        print(f"Error clearing results for client {client_id}: {e}")

@sio.on('plugin.run')
async def run_plugin(sid: str, plugin_args: dict):
    if not state.js:
        return {'status': 'error', 'message': "Server not ready"}

    try:
        message = PluginMessage.model_validate(plugin_args)

        print(f"Received request to run plugin: {message.operation} for client {message.client_id} with args {message.args} and kwargs {message.kwargs}")

        topic = f"plugin.run.{message.client_id}"
        await state.js.publish(topic, message.model_dump_json().encode())

        return message.id

    except ValueError as e:
        return {'status': 'error', 'message': f"Invalid arguments: {str(e)}"}
    except Exception as e:
        print(f"Error running plugin: {e}")
        return {'status': 'error', 'message': "Internal server error"}


if __name__ == '__main__':
    uvicorn.run(app=sio_app, host='0.0.0.0')