import asyncio
import nats

from nats.js.errors import NotFoundError

async def main():
    nc = await nats.connect("nats://localhost:4222")

    await nc.publish("client.page-build", b'')

    await nc.drain()

if __name__ == '__main__':
    asyncio.run(main())