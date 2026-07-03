from typing import Any

from nats.js import JetStreamContext
from nats.js.errors import NotFoundError
from nats.js.api import KeyValueConfig

def short(value:Any, limit:int = 100) -> str:
    """Caps a value's string form for logging - command args/results can be
    screenshots/audio/etc as base64, which must never hit the logs whole."""
    s = str(value)
    return s if len(s) <= limit else f"{s[:limit]}...<+{len(s) - limit} chars>"

async def get_or_create_kv(js:JetStreamContext, bucket_name: str):
    try:
        return await js.key_value(bucket_name)
    except NotFoundError:
        print(f"Bucket '{bucket_name}' not found. Creating...")
        config = KeyValueConfig(bucket=bucket_name, history=5, ttl=None)
        return await js.create_key_value(config)