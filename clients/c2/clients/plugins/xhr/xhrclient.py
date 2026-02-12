from fastapi import APIRouter, Request

from c2.clients.base import Client, ClientRunMessage, register_client


xhrrouter = APIRouter(prefix="/xhr")

class XHRClient(Client):
    router = xhrrouter
    js_plugin = "xhrclient.js"

@xhrrouter.post("/")
async def xhr_endpoint(request: Request, msg:ClientRunMessage):
    client = XHRClient.get_client(request)
    print(f'got message from client {client.id}')
    response = await client.prepare_response(msg.model_dump())
    return response
    

register_client(XHRClient)