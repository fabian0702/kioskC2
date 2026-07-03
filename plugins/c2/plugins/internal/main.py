import nats
import asyncio

from c2.plugins.internal.loader import Loader
from c2.plugins.internal.client_manager import ClientManager


async def connect_nats():
    # depends_on only waits for the nats container to start, not for its
    # JetStream API to actually be ready to accept connections - retry
    # instead of letting a cold-start race crash the whole process.
    while True:
        try:
            return await nats.connect("nats://nats:4222")
        except Exception as e:
            print(f"Failed to connect to NATS, retrying in 2s: {e}")
            await asyncio.sleep(2)


async def main():
    nc = await connect_nats()

    js = nc.jetstream()

    loader = Loader(nc)

    await js.add_stream(name="plugins", subjects=["plugin.run.*", "plugin.response.>"])

    client_manager = ClientManager(nc, loader)
    await client_manager.run()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())