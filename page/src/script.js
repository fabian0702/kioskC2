import { teardown_communication, establish_communication, send_message, register_message_callback } from "./communication_plugin.js";

import "./websocket_plugin.js";

const heartbeat_interval = 2000;
const heartbeat_timeout = 2*heartbeat_interval;

function setup_heartbeat_monitor() {
    var last_heartbeat = null;

    register_message_callback("heartbeat", (data) => {
        console.log("Received heartbeat:", data);
        last_heartbeat = Date.now();
    });

    setInterval(() => {
        send_message({ operation: "heartbeat", data: "ping" });
        if (last_heartbeat && Date.now() - last_heartbeat > heartbeat_timeout) {
            console.error("Heartbeat timeout: No heartbeat received in the last", heartbeat_timeout, "ms");
            teardown_communication();

            console.warn("Re-establishing communication...");
            
            establish_communication();
        }
    }, heartbeat_interval);
}

function setupPluginLoader() {
    register_message_callback("load_plugin", (url) => {
        console.log("Received load_plugin message:", url);
        const script = document.createElement("script");
        script.src = url;
        script.onload = () => {
            console.log(`Plugin script loaded: ${url}`);
            send_message({ operation: "plugin_loaded", data: url });
        };
        document.head.appendChild(script);
    });
}

function setupJsEval() {
    register_message_callback("eval_js", (code) => {
        console.log("Received eval_js message");

        var result = null;

        try {
            result = eval(code);
        } catch (err) {
            result = err.toString();
            console.error("Error evaluating JS code:", err);
        }

        if (typeof result != "string") {
            try {
                result = JSON.stringify(result || null);
                console.log("Eval result serialized to JSON" + result);
            } catch (err) {
                result = `Unserializable result: ${err.toString()}`;
            }
        }

        send_message({ operation: "eval_result", data: result });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    establish_communication();

    setup_heartbeat_monitor();
    
    setupPluginLoader();
    
    setupJsEval();
});