from nats.js import JetStreamContext
from nats.js.errors import NotFoundError
from nats.js.api import KeyValueConfig

async def get_or_create_kv(js:JetStreamContext, bucket_name: str):
    try:
        return await js.key_value(bucket_name)
    except NotFoundError:
        print(f"Bucket '{bucket_name}' not found. Creating...")
        config = KeyValueConfig(bucket=bucket_name, history=5, ttl=None)
        return await js.create_key_value(config)