import asyncio
import os

from c2.plugins.internal.loader import Loader
from c2.plugins.internal.client_manager import ClientManager
from c2.plugins.internal.transport import PluginTransport

INTERNAL_HUB_TOKEN = os.environ["INTERNAL_HUB_TOKEN"]


async def main():
    transport = PluginTransport(INTERNAL_HUB_TOKEN)
    await transport.connect()

    loader = Loader(transport)
    client_manager = ClientManager(transport, loader)

    await transport.sio.wait()

if __name__ == '__main__':
    asyncio.run(main())
