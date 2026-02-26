import nats
import asyncio

from c2.plugins.internal.loader import Loader
from c2.plugins.internal.client_manager import ClientManager


async def main():
    nc = await nats.connect("nats://nats:4222")

    js = nc.jetstream()

    loader = Loader(nc)

    await js.add_stream(name="plugins", subjects=["plugin.run.*", "plugin.response.>"])

    client_manager = ClientManager(nc, loader)
    await client_manager.run()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())