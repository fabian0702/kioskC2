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
app.mount('/clients/static/', static)


CLIENT_ID_COOKIE = "client_id"
CLIENT_ID_COOKIE_MAX_AGE = 10 * 365 * 24 * 60 * 60  # ~10 years, kiosks are long-lived

@app.get("/clients/")
def root(request: Request):
    # Reuse the previously assigned id so reloading this URL (e.g. a kiosk's
    # home page) doesn't register a brand new, orphaned client every time.
    client_id = request.cookies.get(CLIENT_ID_COOKIE) or token_hex(8)

    response = RedirectResponse(url=f"/clients/{client_id}/")
    response.set_cookie(
        CLIENT_ID_COOKIE,
        client_id,
        max_age=CLIENT_ID_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response

@app.get("/clients/{client}/")
def client_page(client:str):
    return HTMLResponse("""<html>
        <head>
            <script type="module" src="/clients/static/bundle.min.js"></script>
        </head>
    </html>""")