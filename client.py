import asyncio
import nats

from nats.js.errors import NotFoundError

from pydantic import BaseModel, Field
from typing import Any, Literal, Optional, Union
from secrets import token_hex

class PluginMessage(BaseModel):
    client_id: str
    id:str = Field(default_factory=lambda : token_hex(16))
    operation: str
    args: list[Any] = []
    kwargs: dict[str, Any] = {}

class ParameterModel(BaseModel):
    name:str
    type:Literal['Literal', 'str', 'float', 'int', 'bool']
    default:Optional[Union[str, float, int, bool]] = None

class ParameterList(BaseModel):
    parameters:list[ParameterModel] = []

async def get_or_create_bucket(nc:nats.NATS, bucket_name: str):
    js = nc.jetstream()
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

async def list_methods(nc:nats.NATS):
    methods:dict[str, ParameterModel] = {}

    #sub = await nc.subscribe('plugins.loaded', max_msgs=1)
    #await sub.next_msg(timeout=10)
    
    methods_bucket = await get_or_create_bucket(nc, 'methods')
    for name in await methods_bucket.keys():
        entry = await methods_bucket.get(name)
        param = ParameterList.model_validate_json(entry.value)

        methods.update({name:param.parameters})

    print(methods)

    return methods

async def main():
    nc = await nats.connect("nats://localhost:4222")
    # asyncio.create_task(list_methods(nc))

    js = nc.jetstream()

    await asyncio.sleep(1)

    render_msg = PluginMessage(client_id='test', operation='website.render', args=['https://mnta.in'])

    await js.add_stream(name="plugins", subjects=["plugin.run.*", "plugin.response.>"])

    await js.publish("plugin.run.test", render_msg.model_dump_json().encode())

    sub = await nc.subscribe(f"plugin.response.test.{render_msg.id}", max_msgs=1)
    response_msg = await sub.next_msg(timeout=30)

    print(f"Received response: {response_msg.data.decode()}")

    await nc.drain()

if __name__ == '__main__':
    asyncio.run(main())