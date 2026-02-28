from c2.plugins.internal.plugins import BasePlugin


class IdlePlugin(BasePlugin):
    name = "idle"
    js_file = "idle.js"

    async def get_idle_time(self) -> float:
        """Returns the number of seconds since the user last interacted with the page.

        Tracked events: mousemove, mousedown, keydown, touchstart, scroll, wheel.
        The JS listener is installed once on first plugin load and persists for
        the lifetime of the page.

        :return: Seconds of inactivity
        :rtype: float
        """
        return await self.methods.eval_js('return window.getIdleTime();')

    async def reset(self) -> None:
        """Resets the idle timer as if the user just interacted with the page.
        """
        await self.methods.eval_js('window.resetIdleTime(); return null;')
