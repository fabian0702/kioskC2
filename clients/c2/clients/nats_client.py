import nats

from c2.clients.base import client_manager, ClientRunMessage


async def run_nats():
    nc = await nats.connect("nats://nats:4222")

    async def send_message(id:str, msg:ClientRunMessage):
        if msg.operation == 'connect':
            print(f"Publishing connection message for client {id}")
            await nc.publish('client.connect', id.encode())
        else:
            print(f"Publishing message client.response.{id}.{msg.id} with operation {msg.operation} and data {msg.data}")
            await nc.publish(f'client.response.{id}.{msg.id}', msg.model_dump_json().encode())

    client_manager.on_msg(send_message)

    sub = await nc.subscribe("client.operations.*")

    async for msg in sub.messages:
        print(f"Received message on subject {msg.subject}: {msg.data}")
        id = msg.subject.removeprefix("client.operations.")
        try:
            parsed_msg = ClientRunMessage.model_validate_json(msg.data)
        except Exception as e:
            print(f"Failed to parse message for client {id} with error {e}")
            continue
        
        client_manager.enqueue_message(id, parsed_msg)

    await sub.unsubscribe()

    await nc.drain()


if __name__ == '__main__':
    import asyncio
    asyncio.run(run_nats())