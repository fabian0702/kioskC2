from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket
from fastapi.templating import Jinja2Templates

from urllib.parse import urlparse

from pydantic import BaseModel

from typing import Callable

class Message(BaseModel):
    operation: str
    data: str

app = FastAPI()

templates = Jinja2Templates(directory="page")

static = StaticFiles(directory='page/')
app.mount('/static/', static)

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("index.html.jinja", {"request": request})

def get_client(websocket: WebSocket):
    hostheader = websocket.headers.get("host")
    host, *_ = hostheader.split(".")
    return host

async def handle_message(message: Message, send_response_callback: Callable[[Message], None]):
    match message.operation:
        case "heartbeat":
            if message.data != "ping":
                None
            # print("heartbeat received")
            return Message(operation="heartbeat", data="pong")
        case _:
            print(f"Unknown operation: {message.operation}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client: str = Depends(get_client)):
    await websocket.accept()

    print(f'got connection from client {client}')

    await websocket.send_json({"operation":"load_plugin", "data":"static/src/example_plugin.js"})
    await websocket.send_json({"operation":"eval_js", "data":"console.log('Hello from server via eval_js');"})

    while True:
        data = await websocket.receive_json()

        message = Message.model_validate(data)

        