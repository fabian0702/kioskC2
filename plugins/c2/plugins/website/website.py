from c2.plugins.internal.plugins import BasePlugin, action
from base64 import b64encode, b64decode

class WebsitePlugin(BasePlugin):
    name = "website"
    js_file = "website.js"
    icon = "fa-window-maximize"

    @action(icon="fa-window-maximize", output="text")
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

    async def picture(self, picture: bytes, fill_height: bool) -> str:
        """Display a picture to fill the page"""

        pic_data_url = "data:;base64,"+picture.replace('-','+').replace('_','/')

        if fill_height:
            bg_size = "auto 100%"
        else:
            bg_size = "100% auto"

        html = f"""<!DOCTYPE html><html><head><style>
        html {{ background-image: url("{pic_data_url}"); 
        background-size: {bg_size};
        width: 100%;
        height: 100%;
        }}
        </style></head></html>"""
        
        
        html_url = await self.methods.serve(html.encode(), extension='html')

        await self.methods.eval_js(f'''
            (async () => {{
                if (!window.load_website_plugin) {{
                    setTimeout(arguments.callee, 100);
                    return;
                }}
                load_website_plugin("{html_url}");                              
            }})()
        ''')

        print("Done")

        return 'website loaded properly'