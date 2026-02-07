
import os
import subprocess

PLUGIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src/plugins/')

NEEDS_REBUILD = False

def add_js_plugin(js_plugin:str):
    if not os.path.exists(PLUGIN_DIR):
        os.makedirs(PLUGIN_DIR)
    
    if not os.path.exists(js_plugin):
        raise FileNotFoundError(f"JS plugin file {js_plugin} not found")
    
    dest_path = os.path.join(PLUGIN_DIR, os.path.basename(js_plugin))

    print(f"Adding JS plugin {js_plugin} to {dest_path}")

    if os.path.exists(dest_path):
        os.remove(dest_path)
    os.symlink(js_plugin, dest_path)

    global NEEDS_REBUILD
    NEEDS_REBUILD = True

def build_dist():
    subprocess.run(['rollup', '-c', 'rollup.config.js'], check=True)

def get_js_dist() -> str:
    global NEEDS_REBUILD
    if NEEDS_REBUILD:
        build_dist()
        NEEDS_REBUILD = False
    
    with open('./dist/bundle.js', 'r') as f:
        return f.read()