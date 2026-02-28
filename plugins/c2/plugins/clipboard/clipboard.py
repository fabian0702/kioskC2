from c2.plugins.internal.plugins import BasePlugin


class ClipboardPlugin(BasePlugin):
    name = "clipboard"

    async def read(self) -> str:
        """Reads the current clipboard text.

        Requires the clipboard-read permission to be granted in the browser.

        :return: Current clipboard text
        :rtype: str
        """
        return await self.methods.eval_js(
            'return navigator.clipboard.readText();'
        )

    async def write(self, text: str) -> None:
        """Writes text to the clipboard.

        :param text: Text to place on the clipboard
        :type text: str
        """
        await self.methods.eval_js(
            f'return navigator.clipboard.writeText({text!r});'
        )
