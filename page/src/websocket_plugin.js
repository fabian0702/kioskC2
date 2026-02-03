import { CommuncationPlugin, register_communication_plugin } from './communication_plugin.js';

class WebsocketPlugin extends CommuncationPlugin {
    ws;
    ws_ready_promise;
    name = "WebsocketPlugin";
    constructor() {
        super();

        this.ws = new WebSocket(`ws://${window.location.host}/ws`);

        this.ws_ready_promise = new Promise((resolve, reject) => {
            this.ws.addEventListener("open", () => {
                    console.log("WebsocketPlugin: Connected to WebSocket");
                    resolve();
                },
                { once: true }
            );

            this.ws.addEventListener("error", (err) => {
                    console.error("WebsocketPlugin: WebSocket error", err);
                    reject(err);
                },
                { once: true }
            );
        });
    }
    
    on_msg(_callback) {
        if (!this.ws || _callback === null) {
            throw new Error("WebsocketPlugin: WebSocket not initialized or callback is null");
        }
        this.ws.addEventListener("message", (event) => {
            _callback(event.data);
        });
    }

    send(data) {
        if (!this.ws || !this.ws_ready_promise) {
            console.warn("WebsocketPlugin: WebSocket not initialized");
            return;
        }
        this.ws_ready_promise
            .then(() => {
                const payload = typeof data === "string" ? data : JSON.stringify(data);
                this.ws.send(payload);
            })
            .catch((err) => {
                console.error("WebsocketPlugin: Failed to send message, WebSocket not ready", err);
            });
    }

    teardown() {
        console.log(`Tearing down communication plugin: ${this.name}`);
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        if (this.ws_ready_promise) {
            this.ws_ready_promise = null;
        }
    }
}

register_communication_plugin(WebsocketPlugin);