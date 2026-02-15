import asyncio

import nats

from nats import NATS
from nats.aio.msg import Msg
from nats.js.errors import BucketNotFoundError

from c2.bundler.fetch import fetch_page
from c2.bundler.preview import preview_page

from pydantic import BaseModel, ValidationError

from secrets import token_hex


class ClientMessage(BaseModel):
    operation: str
    data: dict
    id:str


BUCKET_NAME = "bundler"

async def save_object(nc: NATS, name: str, data: str):
    js = nc.jetstream()

    if isinstance(data, str):
         data = data.encode()

    print(f"Saving {name} into bucket {BUCKET_NAME}")

    try:
        object_store = await js.object_store(BUCKET_NAME)
    except BucketNotFoundError:
        object_store = await js.create_object_store(BUCKET_NAME)
    
    await object_store.put(name, data)

async def handle_fetch_request(url: str, nc: NATS) -> str:
    print(f"Received fetch request for URL: {url}")

    page_data = await fetch_page(url)

    page_name = f"page-{token_hex(8)}"

    print(f'Page Name: {page_name}')

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

    sub = await nc.subscribe("bundler.fetch")
    async for msg in sub.messages:
        try:
            message = ClientMessage.model_validate_json(msg.data)
        except ValidationError as e:
            print(f"Invalid message format: {e}")
            continue

        if not 'url' in message.data:
            print("no url in the request found")
            continue

        match message.operation:
            case "bundle":
                page_name = await handle_fetch_request(message.data.get('url'), nc)
                print(f"Finished building page with name {page_name}")
                await msg.respond(page_name.encode())
            case "preview":
                screenshot_name = await handle_preview_request(nc, message.data.get('url'))
                await msg.respond(screenshot_name.encode())
            case _:
                print(f"Unknown operation: {message.operation}")

if __name__ == '__main__':
    asyncio.run(main())