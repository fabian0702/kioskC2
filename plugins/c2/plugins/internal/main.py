import nats
import json
import asyncio

from nats.js import JetStreamContext
from nats.js.api import KeyValueConfig
from nats.js.errors import NotFoundError

from c2.plugins.internal.loader import Loader
from c2.plugins.internal.client_manager import ClientManager


async def get_or_create_kv(js:JetStreamContext, bucket_name: str):
    try:
        return await js.key_value(bucket_name)
    except NotFoundError:
        print(f"Bucket '{bucket_name}' not found. Creating...")
        config = KeyValueConfig(bucket=bucket_name, history=5, ttl=None)
        return await js.create_key_value(config)

async def main():
    nc = await nats.connect("nats://nats:4222")

    js = nc.jetstream()

    loader = Loader()

    methods = await get_or_create_kv(js, "methods")
    for name, (_, _, params) in loader.methods.items():
        await methods.put(name, params.model_dump_json().encode())

    await nc.publish('plugins.loaded', b'')

    await js.add_stream(name="plugins", subjects=["plugin.run.*", "plugin.response.>"])

    client_manager = ClientManager(nc, loader)
    await client_manager.run()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())