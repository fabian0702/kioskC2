from fastapi import APIRouter, HTTPException
from c2.clients.base import Client
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

class WSClient(Client):
    router = APIRouter(prefix="/ws")

    @staticmethod
    @router.websocket("/")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()

        client_identification:dict = await websocket.receive_json()

        if not 'client' in client_identification:
            raise HTTPException(400, 'missing client identification')
        
        client_id = client_identification.get('client')
        client = WSClient.get_client(client_id)

        print(f'got connection from client {client.id}')

        try:
            while True:
                data = await websocket.receive_json()
                response = await client.prepare_response(data)
                await websocket.send_json(response)
        except WebSocketDisconnect:
            print(f'client {client.id} disconnected')