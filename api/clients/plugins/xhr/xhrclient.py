from fastapi import APIRouter
from api.clients.base import Client, client_manager, register_client, Message
from fastapi import Request

xhrrouter = APIRouter(prefix="/xhr")

class XHRClient(Client):
    router = xhrrouter
    js_plugin = "xhrclient.js"
    
    @staticmethod
    def get_client(request: Request) -> "XHRClient":
        hostheader = request.headers.get("host")
        id, *_ = hostheader.split(".")
        return client_manager.get_client(id, client_class=XHRClient)

@xhrrouter.post("/")
async def xhr_endpoint(request: Request, msg:Message):
    client = XHRClient.get_client(request)
    print(f'got message from client {client.id}')
    response = await client.prepare_response(msg.model_dump())
    return response
    

register_client(XHRClient)