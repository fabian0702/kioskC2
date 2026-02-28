from c2.plugins.internal.plugins import BasePlugin


class AudioPlugin(BasePlugin):
    name = "audio"
    js_file = "audio.js"

    async def record(self, duration: float = 5.0) -> str:
        """Records audio from the client's microphone and returns it as a base64 data URL.

        The browser will prompt for microphone permission if not already granted.
        The recording stops automatically after the given duration.
        The returned data URL is typically audio/webm;codecs=opus (Chrome/Edge) or
        audio/ogg;codecs=opus (Firefox).

        :param duration: Recording duration in seconds. Default 5.
        :type duration: float
        :return: Base64-encoded audio as a data URL (data:audio/...;base64,...)
        :rtype: str
        """
        return await self.methods.eval_js(
            f'return window.recordAudio({duration});',
            timeout=duration + 10,
        )
