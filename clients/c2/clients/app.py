import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from c2.clients.plugins.plugins import *
from c2.clients.base import client_router, client_manager
from c2.clients.nats_client import run_nats
from c2.clients.page.builder import build_dist

import asyncio

async def lifespan(app:FastAPI):
    await build_dist()

    track_heartbeat_task = asyncio.create_task(client_manager.track_heartbeats())

    nats_task = asyncio.create_task(run_nats())

    yield

    nats_task.cancel()
    track_heartbeat_task.cancel()
    
    await nats_task
    await track_heartbeat_task


app = FastAPI(lifespan=lifespan)

app.include_router(client_router)

templates = Jinja2Templates(directory="c2/clients/page")

static = StaticFiles(directory='c2/clients/page/', follow_symlink=True)
app.mount('/static/', static)

plugins = StaticFiles(directory='/plugins/', follow_symlink=True)
app.mount('/plugins/', plugins)


@app.get("/")
def root():
    return RedirectResponse(url="http://test.localhost:8000/client")

@app.get("/client")
def client_page(request: Request):
    return templates.TemplateResponse("index.html.jinja", {"request": request})