import asyncio
import nats

from nats.js.errors import NotFoundError

async def main():
    nc = await nats.connect("nats://localhost:4222")

    js = nc.jetstream()

    await js.publish("manager.operations.test", b'{"operation":"load_plugin", "data":{"url": "static/testplugin.js", "id": "testplugin"}}')
    await js.publish("manager.operations.test", b'{"operation":"eval_js", "data":{"code": "document.body.innerHTML += \'<p>Test message from server</p>\'", "id": "eval1"}}')

    sub = await nc.subscribe("manager.responses.*")

    async for msg in sub.messages:
        id = msg.subject.removeprefix("manager.responses.")

        print(f"received response from client {id}: {msg.data}")

    await nc.drain()

if __name__ == '__main__':
    asyncio.run(main())