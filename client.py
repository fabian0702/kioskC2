import asyncio
import nats

from nats.js.errors import NotFoundError

from pydantic import BaseModel, Field
from typing import Any
from secrets import token_hex

class PluginMessage(BaseModel):
    client_id: str
    id:str = Field(default_factory=lambda : token_hex(16))
    operation: str
    args: list[Any] = []
    kwargs: dict[str, Any] = {}

async def list_methods(nc:nats.NATS):
    js = nc.jetstream()
    try:
        sub = await js.subscribe("plugins.methods")
        methods = []
        async for msg in sub.messages:
            method_name = msg.data.decode()
            print(f"Available method: {method_name}")
            methods.append(method_name)
    except NotFoundError:
        print("No methods found. Make sure the manager is running and has loaded plugins.")

async def main():
    nc = await nats.connect("nats://localhost:4222")
    # asyncio.create_task(list_methods(nc))

    js = nc.jetstream()

    await asyncio.sleep(1)

    render_msg = PluginMessage(client_id='test', operation='website.render', args=['https://mnta.in'])

    await js.add_stream(name="plugins", subjects=["plugin.run.*", "plugin.response.>"])

    await js.publish("plugin.run.test", render_msg.model_dump_json().encode()) #b'{"client_id": "test", "args": ["https://mnta.in"], "kwargs": {}}', timeout=10)
    
    sub = await nc.subscribe(f"plugin.response.test.{render_msg.id}", max_msgs=1)
    response_msg = await sub.next_msg(timeout=10)

    print(f"Received response: {response_msg.data.decode()}")

    await nc.drain()

if __name__ == '__main__':
    asyncio.run(main())