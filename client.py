import asyncio
import nats

from nats.js.errors import NotFoundError

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
    asyncio.create_task(list_methods(nc))

    js = nc.jetstream()

    await asyncio.sleep(1)

    response = await nc.request("plugins.run.website.render", b'{"client_id": "test", "args": ["https://mnta.in"], "kwargs": {}}', timeout=10)
    
    print(f"Received response: {response.data.decode()}")

    await nc.drain()

if __name__ == '__main__':
    asyncio.run(main())