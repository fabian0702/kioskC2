import os
import asyncio
import importlib
import watchfiles
import inspect

from typing import Callable, Literal, Union, Optional, Any

from pydantic import BaseModel

from nats import NATS

from c2.plugins.internal.plugins import BasePlugin
from c2.plugins.internal.utils import get_or_create_kv



PLUGIN_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")

ALLOWED_TYPES = (str, float, int, bool)

class ParameterModel(BaseModel):
    name:str
    type:Literal['Literal', 'str', 'float', 'int', 'bool']
    default:Optional[Union[str, float, int, bool]] = None

    @staticmethod
    def is_allowed_type(val:Any, allow_empty:bool = True) -> bool:
        return val is None or isinstance(val, ALLOWED_TYPES) or val in ALLOWED_TYPES or (allow_empty and val == inspect._empty)

    @classmethod
    def new(cls, param:inspect.Parameter):
        if param.annotation == inspect._empty:
            print(f'argument \'{param.name}\' needs to have a annotation')
            return None
        
        if not cls.is_allowed_type(param.annotation, allow_empty=False):
            print(f'argument \'{param.name}\' needs to be one of these types: {ALLOWED_TYPES}')
            return None
        
        if not cls.is_allowed_type(param.default, allow_empty=True):
            print(f'argument \'{param.name}\' default value needs to one of these types: {ALLOWED_TYPES}')
            return None
        
        default = param.default 

        if default == inspect._empty:
            default = None
        
        return cls(name=param.name, type=param.annotation.__qualname__, default=default)
    
class ParameterList(BaseModel):
    parameters:list[ParameterModel] = []

Method = tuple[Callable, type[BasePlugin], ParameterList]
MethodsDict = dict[str, Method]

class Loader:
    def __init__(self, nc:NATS, plugin_directory:str=PLUGIN_DIRECTORY):
        self.nc = nc
        self.plugin_directory = plugin_directory
        
        self.load_plugins()
        self.load_methods()

        self.hotreload_task = asyncio.create_task(self._hotreload())

    async def _hotreload(self):
        await self._publish()

        async for changes in watchfiles.awatch(self.plugin_directory):
            print(f"Detected changes in plugin directory: {changes}")
            self.load_plugins()
            self.load_methods()
            await self._publish()

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
                    method = (attr, plugin, self.get_args(attr))
                    self.methods.update({f'{name}.{attr_name}': method})

        return self.methods

    def get_args(self, method:Callable) -> ParameterList:
        sig = inspect.signature(method)

        parameter_models = [ParameterModel.new(param) for param in sig.parameters.values() if not param.name == 'self']

        return ParameterList(parameters=[param for param in parameter_models if param is not None])

    async def _publish(self):
        js = self.nc.jetstream()

        methods = await get_or_create_kv(js, "methods")
        for key in await methods.keys():
            await methods.purge(key)
        for name, (_, _, params) in self.methods.items():
            await methods.put(name, params.model_dump_json().encode())

        await self.nc.publish('plugins.loaded')