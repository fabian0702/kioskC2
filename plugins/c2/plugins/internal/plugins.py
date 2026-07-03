from c2.plugins.internal.methods import Methods
from nats import NATS
from typing import Optional, Callable, Literal, Iterable

import os
import inspect
import shutil


def action(
    *,
    icon: Optional[str] = None,
    description: Optional[str] = None,
    output: Optional[Literal['text', 'json', 'image', 'audio', 'code']] = None,
    multiline: Optional[Iterable[str]] = None,
):
    """Optionally annotate a plugin method with metadata for the command execution UI:

    - icon: a FontAwesome icon name (e.g. "fa-camera"). Falls back to the
      plugin's own `icon` attribute when unset.
    - description: a short description. Falls back to the method's docstring
      first line when unset.
    - output: how the result should be rendered ("image", "audio", "json",
      "code", or plain "text"). Left to the UI's own heuristics when unset.
    - multiline: names of string parameters that should get a multi-line/code
      input instead of a single-line text box.
    """
    def decorator(func: Callable) -> Callable:
        if icon is not None:
            func._icon = icon
        if description is not None:
            func._description = description
        if output is not None:
            func._output = output
        if multiline is not None:
            func._multiline = set(multiline)
        return func
    return decorator


class BasePlugin:
    name: str
    js_file: str
    icon: Optional[str] = None
    description: Optional[str] = None
    methods: Methods

    def __init__(self):
        if not hasattr(self, "name"):
            raise NotImplementedError("Plugins must define 'name'")
        
    @classmethod
    async def new(cls, nc:NATS, client_id: str):
        """
        Creates a new instance of the plugin while initializing some internal stuff
        
        :param nc: a instance of nats.py client
        :type nc: NATS
        :param client_id: The id of the client which is interacted with
        :type client_id: str
        :return: returns a new instance of the class
        :rtype: Self
        """
        self = cls()
        self.methods = Methods(nc, client_id)

        if hasattr(self, "js_file"):
            script_path = inspect.getfile(cls)
            js_path = os.path.join(os.path.dirname(script_path), self.js_file)
            if os.path.exists(js_path):
                shutil.copy(js_path, f"/static/{self.js_file}")
                await self.methods.load_js(f"/clients/static/plugins/{self.js_file}")

        return self