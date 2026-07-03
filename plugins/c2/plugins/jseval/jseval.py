from c2.plugins.internal.plugins import BasePlugin, action

class JSEvalPlugin(BasePlugin):
    name = "jseval"
    icon = "fa-code"

    @action(icon="fa-code", output="code")
    async def run(self, code: str) -> str:
        """Runs the provided code in the browser and returns the result"""

        return await self.methods.eval_js(f'var _result = {code}; return _result;')