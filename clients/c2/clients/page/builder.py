
import os
import nats
import shutil

PLUGIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '/plugins/')

def add_js_plugin(js_plugin:str):
    if not os.path.exists(PLUGIN_DIR):
        os.makedirs(PLUGIN_DIR)
    
    if not os.path.exists(js_plugin):
        raise FileNotFoundError(f"JS plugin file {js_plugin} not found")
    
    dest_path = os.path.join(PLUGIN_DIR, os.path.basename(js_plugin))

    print(f"Adding JS plugin {js_plugin} to {dest_path}")

    if os.path.exists(dest_path):
        os.remove(dest_path)
    shutil.copy(js_plugin, dest_path)


async def build_dist():
    nc = await nats.connect("nats://nats:4222")
    await nc.request("client.page-build", b'', timeout=10000)
    await nc.drain()