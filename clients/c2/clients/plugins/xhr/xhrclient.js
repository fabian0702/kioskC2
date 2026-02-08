import { CommuncationPlugin as CommunicationPlugin, register_communication_plugin } from '../communication_plugin.js';

class XhrPlugin extends CommunicationPlugin {
    ws;
    ws_ready_promise;
    name = "XhrPlugin";
    priority = 5;
    constructor() {
        super();

        this.request_url = '/clients/xhr/';

        this._callback = null;
    }

    on_msg(_callback) {
        console.log("XHRPlugin: Registered message callback");
        this._callback = _callback;
    }

    send(data) {
        var response_callback = this._callback;
        var xhr = new XMLHttpRequest();
        xhr.open("POST", this.request_url, true);
        xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    if (response_callback) {
                        try {
                            response_callback(xhr.responseText);
                        } catch (err) {
                            console.error("XHRPlugin: Error in message callback:", err);
                        }
                    } else {
                        console.warn("XHRPlugin: No message callback registered");
                    }
                } else {
                    console.error("XHRPlugin: Failed to send message, status code:", xhr.status);
                }
            }
        };
        try {
            xhr.send(typeof data === "string" ? data : JSON.stringify(data));
        } catch (err) {
            console.error("XHRPlugin: Failed to serialize data for sending", err);
        }
    }

    teardown() {
        console.log(`Tearing down communication plugin: ${this.name}`);
    }
}

register_communication_plugin(XhrPlugin);

export { XhrPlugin };