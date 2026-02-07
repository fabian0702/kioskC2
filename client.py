import asyncio
import nats

async def main():
    # It is very likely that the demo server will see traffic from clients other than yours.
    # To avoid this, start your own locally and modify the example to use it.
    nc = await nats.connect("nats://localhost:4222")

    await nc.publish("client.operations.test", b'{"operation":"load_plugin", "data":{"url": "static/src/plugins/testplugin.js", "id": "testplugin"}}')
    await nc.publish("client.operations.test", b'{"operation":"eval_js", "data":{"code": "document.body.innerHTML += \'<p>Test message from server</p>\'", "id": "eval1"}}')

    sub = await nc.subscribe("client.responses.*")

    async for msg in sub.messages:
        id = msg.subject.removeprefix("client.operations.")

        print(f"received response from client {id}: {msg.data}")

    # Terminate connection to NATS.
    await nc.drain()

if __name__ == '__main__':
    asyncio.run(main())