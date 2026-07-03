import json

import socketio
import uvicorn

from c2.backend.classes import PluginMessage, short
from c2.backend.state import AppState


static_files = {
    '/': '/frontend/',
}

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(sio, static_files=static_files)
state = AppState(sio)


async def request_clients():
    await sio.emit('clients.response', state.get_clients())

state.on_client_connect(request_clients)
state.on_client_disconnect(request_clients)


async def request_methods():
    await sio.emit('methods.response', state.methods)

state.on_plugin_loaded(request_methods)


async def plugin_response(client_id: str):
    await sio.emit(f'plugin.response.{client_id}')

state.on_plugin_response(plugin_response)


@sio.on('results.request')
async def request_results(sid: str, client_id: str):
    await sio.emit(f'results.response.{client_id}', json.dumps(state.get_results(client_id)))

@sio.on('clients.request')
async def get_clients(sid: str):
    await request_clients()

@sio.on('methods.request')
async def get_methods(sid: str):
    await request_methods()

@sio.on('client.remove')
async def remove_client(sid: str, client_id: str):
    state.remove_client(client_id)
    await request_clients()

@sio.on('client.rename')
async def rename_client(sid: str, data: dict):
    client_id = data.get('client_id')
    alias = data.get('alias', '')
    if not client_id:
        return
    state.set_alias(client_id, alias)
    await request_clients()

@sio.on('result.delete')
async def delete_result(sid: str, data: dict):
    client_id = data.get('client_id')
    result_id = data.get('result_id')
    if not client_id or not result_id:
        return
    state.purge_result(client_id, result_id)
    # Tell the plugins service so it cancels the command if it's still
    # running and never writes its result back, even if the client
    # answers after we've already purged it here.
    await state.send_cancel(client_id, result_id)

@sio.on('results.clear')
async def clear_results(sid: str, client_id: str):
    if not client_id:
        return
    for result_id in state.clear_results(client_id):
        await state.send_cancel(client_id, result_id)

@sio.on('plugin.run')
async def run_plugin(sid: str, plugin_args: dict):
    try:
        message = PluginMessage.model_validate(plugin_args)

        print(f"Received request to run plugin: {message.operation} for client {message.client_id} with args {short(message.args)} and kwargs {short(message.kwargs)}")

        dispatched = await state.dispatch_plugin_run(message.model_dump(mode='json'))
        if not dispatched:
            return {'status': 'error', 'message': "Server not ready"}

        return message.id

    except ValueError as e:
        return {'status': 'error', 'message': f"Invalid arguments: {str(e)}"}
    except Exception as e:
        print(f"Error running plugin: {e}")
        return {'status': 'error', 'message': "Internal server error"}


if __name__ == '__main__':
    uvicorn.run(app=sio_app, host='0.0.0.0')
