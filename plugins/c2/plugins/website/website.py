from c2.plugins.internal.plugins import BasePlugin

class WebsitePlugin(BasePlugin):
    name = "website"
    js_file = "website.js"

    async def render(self, url: str, bundle:bool = True) -> str:
        """Fetches the content of the given URL and returns it as a string."""

        if bundle:
            bundled_html = await self.methods.bundle_page(url)
            url = await self.methods.serve(bundled_html, extension='html')

        await self.methods.eval_js(f'''
            (async () => {{
                if (!window.load_website_plugin) {{
                    setTimeout(arguments.callee, 100);
                    return;
                }}
                load_website_plugin("{url}");                              
            }})()
        ''')

        return 'website loaded properly'