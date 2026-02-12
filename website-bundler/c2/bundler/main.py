import asyncio

import nats

from nats import NATS
from nats.aio.msg import Msg
from nats.js.errors import BucketNotFoundError

from c2.bundler.fetch import fetch_page
from c2.bundler.preview import preview_page

from pydantic import BaseModel, ValidationError

from secrets import token_hex

class Message(BaseModel):
    operation: str
    url: str

BUCKET_NAME = "bundler"

async def save_object(nc: NATS, name: str, data: str):
    js = nc.jetstream()

    if isinstance(data, str):
         data = data.encode()

    try:
        object_store = await js.object_store(BUCKET_NAME)
    except BucketNotFoundError:
        object_store = await js.create_object_store(BUCKET_NAME)
    
    await object_store.put(name, data)

async def handle_fetch_request(url: str, nc: NATS) -> str:
    print(f"Received fetch request for URL: {url}")

    page_data = await fetch_page(url)

    page_name = f"page-{token_hex(8)}"

    await save_object(nc, page_name, page_data)

    print(f"Page '{page_name}' saved to object store.")

    return page_name

async def handle_preview_request(nc:NATS, url: str) -> str:
    print(f"Received preview request for URL: {url}")

    screenshot = await preview_page(url)

    print(f"Preview for '{url}' generated.")

    screenshot_name = f"preview-{token_hex(8)}"

    await save_object(nc, screenshot_name, screenshot)

    print(f"Preview '{screenshot_name}' saved to object store.")

    return screenshot_name

async def main():
    nc = await nats.connect("nats://nats:4222")
    js = nc.jetstream()

    await js.add_stream(name="bundler", subjects=["bundler.fetch"])

    sub = await nc.subscribe("bundler.fetch")
    async for msg in sub.messages:
        try:
            message = Message.model_validate_json(msg.data)
        except ValidationError as e:
            print(f"Invalid message format: {e}")
            continue
        match message.operation:
            case "bundle":
                page_name = await handle_fetch_request(message.url, nc)
                await msg.respond(page_name.encode())
            case "preview":
                screenshot_name = await handle_preview_request(nc, message.url)
                await msg.respond(screenshot_name.encode())
            case _:
                print(f"Unknown operation: {message.operation}")

if __name__ == '__main__':
    asyncio.run(main())