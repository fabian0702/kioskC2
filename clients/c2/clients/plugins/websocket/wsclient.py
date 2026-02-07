from fastapi import APIRouter
from c2.clients.base import Client, register_client
from fastapi import WebSocket

wsrouter = APIRouter(prefix="/ws")

class WSClient(Client):
    router = wsrouter
    js_plugin = "wsclient.js"

@wsrouter.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    client = WSClient.get_client(websocket)

    print(f'got connection from client {client.id}')

    while True:
        data = await websocket.receive_json()
        response = await client.prepare_response(data)
        await websocket.send_json(response)

register_client(WSClient)