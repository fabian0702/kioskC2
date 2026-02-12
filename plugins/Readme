# Plugins

This directory contains custom plugins.

## Structure
```
plugins/
├── plugin-name/
│   ├── script.js
│   └── script.py
```
Plugins can either be a communication plugin in which case they must inherit from the [Client Class](../clients/c2/clients/base.py) and be registered with register_client (For a example see ./clients/c2/clients/plugins/xhr/). They can also be a generic plugin which can do any action. The javascript file can get loaded via a load_plugin call or in the case of a properly registered communication plugin it will get built into the client at runtime.

## Methods

Currently the client exposes the `load_plugin` and `eval_js` method which can be used to load a js_file or respecively execute arbitrary js code. For modifications to the dom it is recomended to use document.body only as the head contains all the necessary script / content for communication. If a whole page should be embedded a iframe is recomended to do it. There is also a service to bundle / take a screenshot of a arbitrary website if thats necessary.