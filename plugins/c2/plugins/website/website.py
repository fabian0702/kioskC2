from c2.plugins.internal.plugins import BasePlugin

class WebsitePlugin(BasePlugin):
    name = "website"
    js_file = "website.js"

    async def render(self, url: str) -> str:
        """Fetches the content of the given URL and returns it as a string."""
        print('Running method website.render')
        return await self.methods.eval_js(f'''
            (async () => {{
                if (!window.load_website_plugin) {{
                    setTimeout(arguments.callee, 100);
                    return;
                }}
                load_website_plugin("{url}");                              
            }})()
        ''')