import nats

from c2.clients.base import client_manager, Message


async def run_nats():
    nc = await nats.connect("nats://nats:4222")

    async def send_message(id:str, msg:Message):
        await nc.publish(f'client.responses.{id}', msg.model_dump_json().encode())

    client_manager.on_msg(send_message)

    sub = await nc.subscribe("client.operations.*")

    async for msg in sub.messages:
        print(f"Received message on subject {msg.subject}: {msg.data}")
        id = msg.subject.removeprefix("client.operations.")
        parsed_msg = Message.model_validate_json(msg.data)
        
        client_manager.enqueue_message(id, parsed_msg)

    await sub.unsubscribe()

    await nc.drain()


if __name__ == '__main__':
    import asyncio
    asyncio.run(run_nats())