import { CommuncationPlugin as CommunicationPlugin, register_communication_plugin } from '../communication_plugin.js';

class WebsocketPlugin extends CommunicationPlugin {
    ws;
    ws_ready_promise;
    name = "WebsocketPlugin";
    priority = 10;
    constructor() {
        super();

        this.ws = new WebSocket(`ws://${window.location.host}/clients/ws/`);

        this.ws.addEventListener("open", () => {
            console.log("WebsocketPlugin: Connected to WebSocket");
        });

        this.ws.addEventListener("error", (err) => {
            console.error("WebsocketPlugin: WebSocket error", err);
            this.ws = null;
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
        const retry = (attempts = 0, maxAttempts = 5, delay = 100) => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                const payload = typeof data === "string" ? data : JSON.stringify(data);
                this.ws.send(payload);
            } else if (attempts < maxAttempts) {
                setTimeout(() => retry(attempts + 1, maxAttempts, delay), delay);
            } else {
                console.error("WebsocketPlugin: Failed to send message after retries");
            }
        };
        retry();
    }

    teardown() {
        console.log(`Tearing down communication plugin: ${this.name}`);
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

register_communication_plugin(WebsocketPlugin);

export { WebsocketPlugin };