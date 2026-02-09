import asyncio

import nats

from nats import NATS
from nats.aio.msg import Msg
from nats.js.errors import BucketNotFoundError

from c2.bundler.fetch import fetch_page

BUCKET_NAME = "pages"

async def save_page(nc: NATS, page_name: str, page_data: str):
    js = nc.jetstream()

    try:
        object_store = await js.object_store(BUCKET_NAME)
    except BucketNotFoundError:
        object_store = await js.create_object_store(BUCKET_NAME)
    
    await object_store.put(page_name, page_data.encode())

async def handle_fetch_request(msg:Msg, nc: NATS) -> str:
    url = msg.data.decode()
    print(f"Received fetch request for URL: {url}")

    page_name, page_data = await fetch_page(url)

    await save_page(nc, page_name, page_data)

    print(f"Page '{page_name}' saved to object store.")

    return page_name

async def main():
    nc = await nats.connect("nats://nats:4222")
    js = nc.jetstream()

    await js.add_stream(name="bundler", subjects=["bundler.fetch"])

    sub = await nc.subscribe("bundler.fetch")
    async for msg in sub.messages:
        page_name = await handle_fetch_request(msg, nc)
        await msg.respond(page_name.encode())

if __name__ == '__main__':
    asyncio.run(main())