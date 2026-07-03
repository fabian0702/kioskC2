from fastapi import APIRouter, Request

from c2.clients.base import Client, ClientRunMessage


class XHRClient(Client):
    router = APIRouter(prefix="/xhr")

    @staticmethod
    @router.post("/{client_id}/")
    async def xhr_endpoint(client_id:str, msg:ClientRunMessage):
        client = XHRClient.get_client(client_id)
        print(f'got message from client {client.id}')
        response = await client.prepare_response(msg.model_dump())
        return response