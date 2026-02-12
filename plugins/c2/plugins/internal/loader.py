import os
import importlib
import inspect

from typing import Any, Callable

from nats import NATS

from c2.plugins.internal.plugins import BasePlugin

MethodsDict = dict[str, tuple[Callable, type[BasePlugin]]]


PLUGIN_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")


class Loader:
    def __init__(self, plugin_directory:str=PLUGIN_DIRECTORY):
        self.plugin_directory = plugin_directory

        self.load_plugins()
        self.load_methods()

    def load_plugin(self, module_path:str) -> type[BasePlugin] | None:
        print(f"Loading plugin module: {module_path}")
        module = importlib.import_module(f"c2.plugins.{module_path}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                print(f"Loaded plugin: {attr.name}")

                return attr
            
    def load_plugins(self) -> dict[str, type[BasePlugin]]:
        self.plugins:dict[str, type[BasePlugin]] = {}
        for dirpath, _, filenames in os.walk(self.plugin_directory):
            for filename in filenames:
                if filename.endswith(".py") and not filename.startswith("__"):
                    module_path = os.path.relpath(os.path.join(dirpath, filename), self.plugin_directory)[:-3].replace(os.sep, ".")
                    if 'internal' in module_path:
                        continue
                    plugin = self.load_plugin(module_path)
                    if plugin:
                        self.plugins[plugin.name] = plugin

        print(f"Total plugins loaded: {len(self.plugins)}")

        return self.plugins
    
    def load_methods(self) -> MethodsDict:
        self.methods:MethodsDict = {}

        for name, plugin in self.plugins.items():
            for attr_name, attr in inspect.getmembers(plugin):
                if inspect.isfunction(attr) and not attr_name.startswith("_"):
                    self.methods.update({f'{name}.{attr_name}': (attr, plugin)})

        return self.methods