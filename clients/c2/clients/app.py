import asyncio

from secrets import token_hex

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse

from c2.clients.plugins.plugins import *
from c2.clients.base import client_manager
from c2.clients.nats_client import run_nats

import os
import asyncio

EXTERNAL_URL = os.environ.get('EXTERNAL_URL', 'localhost')

async def lifespan(app:FastAPI):
    track_heartbeat_task = asyncio.create_task(client_manager.track_heartbeats())

    nats_task = asyncio.create_task(run_nats())

    yield

    nats_task.cancel()
    track_heartbeat_task.cancel()
    
    await nats_task
    await track_heartbeat_task


app = FastAPI(lifespan=lifespan)

app.include_router(client_manager.router)

static = StaticFiles(directory='/static/')
app.mount('/static/', static)


@app.get("/")
def root():
    return RedirectResponse(url=f"http://{token_hex(8)}.clients.{EXTERNAL_URL}/client")

@app.get("/client")
def client_page():
    return HTMLResponse("""<html>
        <head>
            <script type="module" src="/static/bundle.min.js"></script>
        </head>
    </html>""")