import nats
import json
import asyncio

from nats.js import JetStreamContext
from nats.js.errors import NotFoundError

from c2.plugins.internal.loader import Loader
from c2.plugins.internal.client_manager import ClientManager


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

async def main():
    nc = await nats.connect("nats://nats:4222")

    js = nc.jetstream()

    loader = Loader()

    methods = await get_or_create_bucket(js, "methods")
    await methods.put("methods", json.dumps(list(loader.methods.keys())).encode())

    await js.add_stream(name="plugins", subjects=["plugin.run.*", "plugin.response.>"])

    client_manager = ClientManager(nc, loader)
    await client_manager.run()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())