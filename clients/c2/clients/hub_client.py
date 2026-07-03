import asyncio
import os

import socketio

from c2.clients.base import client_manager, ClientRunMessage, _short

HUB_URL = "http://ui:8000"
NAMESPACE = "/internal/clients"
INTERNAL_HUB_TOKEN = os.environ["INTERNAL_HUB_TOKEN"]

sio = socketio.AsyncClient()


@sio.on("device.command", namespace=NAMESPACE)
async def handle_device_command(payload: dict):
    client_id = payload.get("client_id")
    if not client_id:
        return

    try:
        parsed_msg = ClientRunMessage.model_validate(payload.get("message"))
    except Exception as e:
        print(f"Failed to parse device command for client {client_id} with error {e}")
        return

    try:
        await client_manager.enqueue_message(client_id, parsed_msg)
    except Exception as e:
        # A single client's stale/reconnecting websocket must not kill
        # this consumer for every other client.
        print(f"Failed to enqueue message for client {client_id} with error {e}")


async def run_hub_client():
    async def handle_msg(id: str, msg: ClientRunMessage):
        print(f"Sending response for client {id} with operation {msg.operation} and data {_short(msg.data)}")
        await sio.emit("device.response", {"client_id": id, "message": msg.model_dump(mode="json")}, namespace=NAMESPACE)

    client_manager.on_msg(handle_msg)

    async def handle_connect(id: str, user_agent=None):
        await sio.emit("client.connect", {"client_id": id, "user_agent": user_agent}, namespace=NAMESPACE)

    client_manager.on_connect(handle_connect)

    async def handle_disconnect(id: str, last_seen: float, user_agent=None):
        await sio.emit("client.disconnect", {"client_id": id, "last_seen": last_seen, "user_agent": user_agent}, namespace=NAMESPACE)

    client_manager.on_disconnect(handle_disconnect)

    async def handle_heartbeat(id: str, last_seen: float, user_agent=None):
        await sio.emit("client.heartbeat", {"client_id": id, "last_seen": last_seen, "user_agent": user_agent}, namespace=NAMESPACE)

    client_manager.on_heartbeat(handle_heartbeat)

    # depends_on only waits for the ui container to start, not for it to
    # actually be ready to accept connections - retry instead of letting a
    # cold-start race crash the whole process.
    while True:
        try:
            await sio.connect(HUB_URL, namespaces=[NAMESPACE], auth={"token": INTERNAL_HUB_TOKEN})
            break
        except socketio.exceptions.ConnectionError as e:
            print(f"Failed to connect to hub, retrying in 2s: {e}")
            await asyncio.sleep(2)

    await sio.wait()


async def run_hub_client_supervised():
    """Restarts run_hub_client() if it ever dies from an unhandled exception,
    instead of silently leaving the hub connection dead for the process's
    lifetime. run_hub_client() only returns normally when cancelled (shutdown)."""
    while True:
        try:
            await run_hub_client()
            return
        except asyncio.CancelledError:
            if sio.connected:
                await sio.disconnect()
            raise
        except Exception as e:
            print(f"run_hub_client() crashed, restarting in 2s: {e}")
            await asyncio.sleep(2)


if __name__ == '__main__':
    asyncio.run(run_hub_client())
