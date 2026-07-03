from fastapi import APIRouter
from c2.clients.base import Client, ClientRunMessage
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

class WSClient(Client):
    router = APIRouter(prefix="/ws")

    websocket: WebSocket

    @staticmethod
    @router.websocket("/")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()

        client_identification:dict = await websocket.receive_json()

        if not 'client' in client_identification:
            await websocket.close(code=4400, reason='missing client identification')
            return

        client_id = client_identification.get('client')
        client:WSClient = WSClient.get_client(client_id)

        client.websocket = websocket

        print(f'got connection from client {client.id}')

        try:
            while True:
                data = await websocket.receive_json()
                response = await client.prepare_response(data)
                await websocket.send_json(response)
        except WebSocketDisconnect:
            print(f'client {client.id} disconnected')
        except Exception as e:
            print(f'client {client.id} error: {e}')
            await websocket.close(code=1011)


    async def enqueue_message(self, message:ClientRunMessage):
        await self.websocket.send_json([message.model_dump()])