import asyncio

import nats

from c2.manager.client import ClientManager

async def main():
    print("Starting manager...")
    nc = await nats.connect("nats://nats:4222")
    js = nc.jetstream()

    await js.add_stream(name="manager", subjects=["manager.operations.*"])

    client_manager = ClientManager(nc)

    sub = await nc.subscribe("client.connect")
    async for msg in sub.messages:
        id = msg.data.decode()

        print(f"Received connection from client {id}")

        client_manager.connect_client(id)

    await nc.drain()

if __name__ == '__main__':
    asyncio.run(main())