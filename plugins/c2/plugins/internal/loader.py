import os
import re
import sys
import asyncio
import importlib
import watchfiles
import inspect

import nats.js.errors

from typing import Callable, Literal, Union, Optional, Any, get_origin, get_args

from pydantic import BaseModel

from nats import NATS

from c2.plugins.internal.plugins import BasePlugin
from c2.plugins.internal.utils import get_or_create_kv



PLUGIN_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")

ALLOWED_TYPES = (str, float, int, bool)

PARAM_DOC_RE = re.compile(r':param\s+(\w+)\s*:\s*(.*?)(?=\n\s*:\w|\Z)', re.DOTALL)

class ParameterModel(BaseModel):
    name:str
    type:Literal['Literal', 'str', 'float', 'int', 'bool']
    default:Optional[Union[str, float, int, bool]] = None
    choices:Optional[list[Union[str, float, int, bool]]] = None
    multiline:bool = False
    description:str = ""

    @staticmethod
    def is_allowed_type(val:Any, allow_empty:bool = True) -> bool:
        return val is None or isinstance(val, ALLOWED_TYPES) or val in ALLOWED_TYPES or (allow_empty and val == inspect._empty)

    @classmethod
    def new(cls, param:inspect.Parameter, multiline:bool = False, description:str = ""):
        annotation = param.annotation

        if annotation == inspect._empty:
            print(f'argument \'{param.name}\' needs to have a annotation')
            return None

        choices = None

        if get_origin(annotation) is Literal:
            choices = list(get_args(annotation))
            if not choices or not all(cls.is_allowed_type(c, allow_empty=False) for c in choices):
                print(f'argument \'{param.name}\' Literal choices need to be one of these types: {ALLOWED_TYPES}')
                return None
            type_name = 'Literal'
        else:
            if not cls.is_allowed_type(annotation, allow_empty=False):
                print(f'argument \'{param.name}\' needs to be one of these types: {ALLOWED_TYPES}')
                return None
            type_name = annotation.__qualname__

        if not cls.is_allowed_type(param.default, allow_empty=True):
            print(f'argument \'{param.name}\' default value needs to one of these types: {ALLOWED_TYPES}')
            return None

        default = param.default

        if default == inspect._empty:
            default = None

        return cls(name=param.name, type=type_name, default=default, choices=choices, multiline=multiline, description=description)

class MethodModel(BaseModel):
    description:str = ""
    icon:Optional[str] = None
    output:Optional[Literal['text', 'json', 'image', 'audio', 'code']] = None
    parameters:list[ParameterModel] = []

Method = tuple[Callable, type[BasePlugin], MethodModel]
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
            if any('internal' in path for _, path in changes):
                self._reload_internals()
            self.load_plugins()
            self.load_methods()
            await self._publish()

    def load_plugin(self, module_path:str) -> type[BasePlugin] | None:
        print(f"Loading plugin module: {module_path}")
        module_name = f"c2.plugins.{module_path}"
        if module_name in sys.modules:
            module = importlib.reload(sys.modules[module_name])
        else:
            module = importlib.import_module(module_name)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                print(f"Loaded plugin: {attr.name}")

                return attr
            
    def _reload_internals(self):
        # Reload methods.py so changes (e.g. new parameters) are picked up.
        # We deliberately do NOT reload plugins.py because that would create a new
        # BasePlugin class object and break the issubclass() check below.
        # Instead we patch the Methods reference inside plugins.py directly.
        methods_mod = sys.modules.get('c2.plugins.internal.methods')
        plugins_mod = sys.modules.get('c2.plugins.internal.plugins')
        if methods_mod:
            importlib.reload(methods_mod)
        if plugins_mod and methods_mod:
            plugins_mod.Methods = methods_mod.Methods

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
                    method = (attr, plugin, self.get_method_info(attr, plugin))
                    self.methods.update({f'{name}.{attr_name}': method})

        return self.methods

    def get_args(self, method:Callable) -> list[ParameterModel]:
        sig = inspect.signature(method)
        multiline_params = getattr(method, '_multiline', set())
        param_docs = self._parse_param_docs(method)

        parameter_models = [
            ParameterModel.new(
                param,
                multiline=param.name in multiline_params,
                description=param_docs.get(param.name, ""),
            )
            for param in sig.parameters.values() if not param.name == 'self'
        ]

        return [param for param in parameter_models if param is not None]

    def get_method_info(self, method:Callable, plugin:type[BasePlugin]) -> MethodModel:
        description = getattr(method, '_description', None) or self._first_doc_line(method) or getattr(plugin, 'description', None) or ""
        icon = getattr(method, '_icon', None) or getattr(plugin, 'icon', None)
        output = getattr(method, '_output', None)

        return MethodModel(description=description, icon=icon, output=output, parameters=self.get_args(method))

    @staticmethod
    def _first_doc_line(method:Callable) -> str:
        doc = inspect.getdoc(method)
        if not doc:
            return ""
        return doc.strip().splitlines()[0].strip()

    @staticmethod
    def _parse_param_docs(method:Callable) -> dict[str, str]:
        """Extracts ':param name: description' entries from the method's docstring."""
        doc = inspect.getdoc(method)
        if not doc:
            return {}

        docs = {}
        for name, desc in PARAM_DOC_RE.findall(doc):
            docs[name] = ' '.join(line.strip() for line in desc.strip().splitlines())
        return docs

    async def _publish(self):
        js = self.nc.jetstream()

        methods = await get_or_create_kv(js, "methods")
        try:
            for key in await methods.keys():
                await methods.purge(key)
        except nats.js.errors.NoKeysError:
            pass
        for name, (_, _, params) in self.methods.items():
            await methods.put(name, params.model_dump_json().encode())

        await self.nc.publish('plugins.loaded')