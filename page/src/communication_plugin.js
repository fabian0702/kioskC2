var plugins = [];
var on_message_callbacks = [];
var plugin_send_function = null;
var active_plugin = null;

class CommuncationPlugin {
    name;
    on_msg_callback;
    on_msg(_callback) {
        throw new Error("CommuncationPlugin.on_msg() must be overridden by a child class");
    }

    send(_data) {
        throw new Error("CommuncationPlugin.send() must be overridden by a child class");
    }

    teardown() {
        console.log(`Tearing down communication plugin: ${this.name}`);
    }
}

function register_communication_plugin(plugin) {
    console.log("Registering communication plugin:", plugin.name);

    if (typeof plugin !== "function" || !(plugin.prototype instanceof CommuncationPlugin)) {
        throw new Error("Plugin must be a class that extends CommuncationPlugin");
    }

    plugins.push(plugin);
}

function find_plugin() {
    for (const PluginClass of plugins) {
        try {
            const plugin_instance = new PluginClass();
            console.log(`Established communication with plugin: ${PluginClass.name}`);
            return plugin_instance;
        } catch (err) {
            console.error(`Failed to establish communication with plugin: ${PluginClass.name}`, err);
        }
    }
}

function establish_communication() {
    console.log("Establishing communication...");
    active_plugin = find_plugin();
    if (!active_plugin) {
        throw new Error("No communication plugin could be established");
    }

    active_plugin.on_msg((msg) => {
        console.log("Received message:", msg);
        try {
            if (typeof msg === "string") 
                msg = JSON.parse(msg);
        } catch (err) {
            console.error("Failed to parse incoming message as JSON:", msg, err);
            return;
        }
        let operation = msg?.operation;
        let data = msg?.data;

        if (!operation) {
            console.error("Received message without operation:", msg);
            return;
        }
        const callbacks = on_message_callbacks[operation] || [];
        if (callbacks.length === 0) {
            console.warn(`No callbacks registered for operation: ${operation}`);
            return;
        }
        callbacks.forEach((callback) => callback(data));
    });

    plugin_send_function = active_plugin.send.bind(active_plugin);

    return active_plugin;
}

function send_message(data) {
    if (!plugin_send_function) {
        throw new Error("Communication plugin not established");
    }
    plugin_send_function(data);
}

function register_message_callback(operation, callback) {
    if (!on_message_callbacks[operation]) {
        on_message_callbacks[operation] = [];
    }
    on_message_callbacks[operation].push(callback);
}

function teardown_communication() {
    active_plugin.teardown();
    active_plugin = null;
    plugin_send_function = null;
    on_message_callbacks = [];
}

export {
    CommuncationPlugin, 
    register_communication_plugin,
    establish_communication,
    teardown_communication,
    send_message,
    register_message_callback,
};