import asyncio
import nats

async def main():
    nc = await nats.connect("nats://localhost:4222")

    response = await nc.request("bundler.fetch", b'https://mnta.in/')
    print(f"Received response: {response.data.decode()}")

    js = nc.jetstream()
    object_store = await js.object_store("bundler")
    page_data = await object_store.get(response.data.decode())
    print(f"Page data: {page_data.data.decode()}")

    await nc.drain()

if __name__ == '__main__':
    asyncio.run(main())