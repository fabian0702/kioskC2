from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.clients.clients import client_router, client_manager, Message

app = FastAPI()

app.include_router(client_router)

templates = Jinja2Templates(directory="page")

static = StaticFiles(directory='page/', follow_symlink=True)
app.mount('/static/', static)

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("dev.html.jinja", {"request": request})

client_manager.enqueue_message("test", Message(operation="load_plugin", data={"url": "static/src/plugins/testplugin.js", "id": "testplugin"}))
client_manager.enqueue_message("test", Message(operation="eval_js", data={"code": "document.body.innerHTML += '<p>Test message from server</p>'", "id": "eval1"}))