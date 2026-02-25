from fastapi import APIRouter, Request

from c2.clients.base import Client, ClientRunMessage


class XHRClient(Client):
    router = APIRouter(prefix="/xhr")

    @staticmethod
    @router.post("/")
    async def xhr_endpoint(request: Request, msg:ClientRunMessage):
        client = XHRClient.get_client(request)
        print(f'got message from client {client.id}')
        response = await client.prepare_response(msg.model_dump())
        return response