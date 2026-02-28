from c2.plugins.internal.plugins import BasePlugin


class CameraPlugin(BasePlugin):
    name = "camera"
    js_file = "camera.js"

    async def capture(self, facing: str = "user", scale: float = 1.0) -> str:
        """Captures a photo from the device camera and returns it as a base64 JPEG.

        The browser will prompt for camera permission if not already granted.
        The stream is stopped immediately after the frame is taken.

        :param facing: Which camera to use — "user" (front) or "environment" (rear).
        :type facing: str
        :param scale: Resolution scale factor (0.1–1.0). Default 1.0 (native resolution).
        :type scale: float
        :return: Base64-encoded JPEG as a data URL (data:image/jpeg;base64,...)
        :rtype: str
        """
        return await self.methods.eval_js(
            f'return window.takePhoto({facing!r}, {scale});'
        )
