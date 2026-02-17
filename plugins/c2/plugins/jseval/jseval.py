from c2.plugins.internal.plugins import BasePlugin

class JSEvalPlugin(BasePlugin):
    name = "jseval"

    async def run(self, code: str) -> str:
        """Runs the provided code in the browser and returns the result"""

        return await self.methods.eval_js(f'var _result = {code}; return _result;')