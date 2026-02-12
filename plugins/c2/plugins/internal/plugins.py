from c2.plugins.internal.methods import Methods
from nats import NATS

import os
import inspect
import shutil

class BasePlugin:
    name: str
    js_file: str
    methods: Methods

    def __init__(self):
        if not hasattr(self, "name"):
            raise NotImplementedError("Plugins must define 'name'")
    
    @classmethod
    async def new(cls, nc:NATS, client_id: str):
        """Called when the plugin is loaded. Can be used to perform any setup or initialization."""
        self = cls()
        self.methods = Methods(nc, client_id)

        if hasattr(self, "js_file"):
            script_path = inspect.getfile(cls)
            js_path = os.path.join(os.path.dirname(script_path), self.js_file)
            if os.path.exists(js_path):
                shutil.copy(js_path, f"/plugins/{self.js_file}")
                await self.methods.load_plugin(f"/plugins/{self.js_file}")

        return self