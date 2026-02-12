import os
import nats
import json
import inspect
import importlib

from typing import Callable, Any
from pydantic import BaseModel
from nats import NATS

from c2.plugins.internal.plugins import BasePlugin

class Message(BaseModel):
    client_id: str
    args: list[Any] = []
    kwargs: dict[str, Any] = {}


PLUGIN_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")


async def _load_plugin(module_path:str) -> type[BasePlugin] | None:
    print(f"Loading plugin module: {module_path}")
    module = importlib.import_module(f"c2.plugins.{module_path}")
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
            print(f"Loaded plugin: {attr.name}")

            return attr

async def _load_plugins(plugin_directory: str) -> dict[str, type[BasePlugin]]:
    plugins:dict[str, type[BasePlugin]] = {}
    for dirpath, _, filenames in os.walk(plugin_directory):
        for filename in filenames:
            if filename.endswith(".py") and not filename.startswith("__"):
                module_path = os.path.relpath(os.path.join(dirpath, filename), PLUGIN_DIRECTORY)[:-3].replace(os.sep, ".")
                if 'internal' in module_path:
                    continue
                plugin = await _load_plugin(module_path)
                if plugin:
                    plugins[plugin.name] = plugin

    print(f"Total plugins loaded: {len(plugins)}")

    return plugins

async def main():
    nc = await nats.connect("nats://nats:4222")
    plugins = await _load_plugins(PLUGIN_DIRECTORY)

    methods:dict[str, Callable[[NATS, str, Any], Any]] = {}
    for name, plugin in plugins.items():
        for attr_name, attr in inspect.getmembers(plugin):
            if inspect.isfunction(attr) and not attr_name.startswith("_"):
                methods.update({f'{name}.{attr_name}': attr})

    js = nc.jetstream()
    await js.add_stream(name="plugins", subjects=["plugins.methods"])
    for method_name in methods.keys():
        await js.publish(f"plugins.methods", method_name.encode())

    sub = await nc.subscribe(f"plugins.run.>")

    async for msg in sub.messages:
        operation = msg.subject.removeprefix("plugins.run.")
        if operation in methods:
            data = Message.model_validate_json(msg.data.decode())
            method = methods[operation]

            plugin_instance = await plugin.new(nc, data.client_id)

            print(f"Executing plugin method '{operation}' with args {data.args} and kwargs {data.kwargs}")
            
            result = await method(plugin_instance, *data.args, **data.kwargs)
            await msg.respond(json.dumps(result).encode())
        else:
            print(f"Unknown plugin operation: {operation}")
    

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())