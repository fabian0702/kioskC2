from typing import Optional

import nats

from nats import NATS
from nats.js import JetStreamContext
from nats.js.kv import KeyValue
from nats.js.api import KeyValueConfig
from nats.js.errors import BucketNotFoundError


NATS_URL = "nats://nats:4222"


class AppState:
    """
    Encapsulates the application state to ensure type safety 
    and avoid global variables.
    """
    def __init__(self):
        self.nc: Optional[NATS] = None
        self.js: Optional[JetStreamContext] = None
        self.method_kv: Optional[KeyValue] = None
        self.client_kv: Optional[KeyValue] = None

    async def startup(self):
        print(f"Connecting to NATS at {NATS_URL}...")
        self.nc = await nats.connect(NATS_URL)
        self.js = self.nc.jetstream()
        
        self.method_kv = await self._get_or_create_kv('methods')
        self.client_kv = await self._get_or_create_kv('clients')
        print("Startup complete")

    async def shutdown(self):
        if self.nc:
            await self.nc.drain()
            await self.nc.close()
            print("Shutdown complete")
    
    async def _get_or_create_kv(self, bucket_name: str) -> KeyValue:
        """Internal helper to fetch or create a KV bucket."""
        if not self.js:
            raise RuntimeError("JetStream context not initialized")

        try:
            return await self.js.key_value(bucket_name)
        except BucketNotFoundError:
            print(f"Bucket '{bucket_name}' not found. Creating...")
            config = KeyValueConfig(bucket=bucket_name, history=5)
            return await self.js.create_key_value(config)

