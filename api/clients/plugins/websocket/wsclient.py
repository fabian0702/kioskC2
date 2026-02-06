from fastapi import APIRouter
from api.clients.base import Client, client_manager, register_client
from fastapi import WebSocket

wsrouter = APIRouter(prefix="/ws")

class WSClient(Client):
    router = wsrouter
    js_plugin = "wsclient.js"
    
    @staticmethod
    def get_client(websocket: WebSocket) -> "WSClient":
        hostheader = websocket.headers.get("host")
        id, *_ = hostheader.split(".")
        return client_manager.get_client(id, client_class=WSClient)

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