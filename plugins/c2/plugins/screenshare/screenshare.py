from c2.plugins.internal.plugins import BasePlugin


class ScreenSharePlugin(BasePlugin):
    name = "screenshare"
    js_file = "screenshare.js"

    async def capture(self, scale: float = 1.0) -> str:
        """Captures a single frame of the screen/window/tab selected by the user
        via the browser's Screen Capture API (getDisplayMedia) and returns it as
        a base64 JPEG data URL.

        The browser will show a native screen-picker dialog asking the user to
        choose which screen, window, or tab to share.  The stream is stopped
        immediately after the frame is taken.

        :param scale: Resolution scale factor (0.1–1.0). Lower values produce
            smaller images.  Defaults to 1.0 (native resolution).
        :type scale: float
        :return: Base64-encoded JPEG as a data URL (data:image/jpeg;base64,...)
        :rtype: str
        """
        return await self.methods.eval_js(f'return window.takeScreenShare({scale});', timeout=120)
