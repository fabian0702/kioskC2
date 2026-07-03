import uuid

from c2.plugins.internal.plugins import BasePlugin, action


class RemoteJSPlugin(BasePlugin):
    name = "remotejs"
    icon = "fa-bug"
    description = "Attach a remotejs.com live console for remote debugging"

    @action(icon="fa-bug", output="text")
    async def attach(self) -> str:
        """Injects the remotejs.com console agent into the page and returns a viewer URL.

        Opening the returned URL in any browser gives a live, interactive view of
        the client's console (logs, errors, warnings) via remotejs.com.

        :return: The https://remotejs.com/viewer/<channel> URL to open.
        :rtype: str
        """
        channel = str(uuid.uuid4())

        await self.methods.eval_js(
            '(function(){'
            'var s=document.createElement("script");'
            's.src="https://remotejs.com/agent/agent.js";'
            f's.setAttribute("data-consolejs-channel","{channel}");'
            'document.head.appendChild(s);'
            '})()'
        )

        return f"https://remotejs.com/viewer/{channel}"
