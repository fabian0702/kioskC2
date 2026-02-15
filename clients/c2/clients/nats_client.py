import nats

from nats.js import JetStreamContext
from nats.js.errors import NotFoundError

from c2.clients.base import client_manager, ClientRunMessage

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
    nc = await nats.connect("nats://nats:4222")
    js = nc.jetstream()

    clients_bucket = await get_or_create_bucket(js, 'clients')

    async def send_message(id:str, msg:ClientRunMessage):
        if msg.operation == 'connect':
            print(f"Publishing connection message for client {id}")
            await nc.publish('client.connect', id.encode())
            await clients_bucket.put(id, b'connected')
        else:
            print(f"Publishing message client.response.{id}.{msg.id} with operation {msg.operation} and data {msg.data}")
            await nc.publish(f'client.response.{id}.{msg.id}', msg.model_dump_json().encode())

    client_manager.on_msg(send_message)

    async def handle_disconnect(id:str):
        await nc.publish('client.disconnect', id.encode())
        await clients_bucket.put(id, b'connected')

    client_manager.on_disconnect(handle_disconnect)

    sub = await nc.subscribe("client.operations.*")

    async for msg in sub.messages:
        print(f"Received message on subject {msg.subject}: {msg.data}")
        id = msg.subject.removeprefix("client.operations.")
        try:
            parsed_msg = ClientRunMessage.model_validate_json(msg.data)
        except Exception as e:
            print(f"Failed to parse message for client {id} with error {e}")
            continue
        
        client_manager.enqueue_message(id, parsed_msg)

    await sub.unsubscribe()

    await nc.drain()


if __name__ == '__main__':
    import asyncio
    asyncio.run(run_nats())