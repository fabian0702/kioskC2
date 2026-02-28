(function () {
    /**
     * Records audio from the microphone for the given duration and returns
     * a base64-encoded audio data URL (typically audio/webm;codecs=opus).
     *
     * @param {number} duration - Recording duration in seconds. Default 5.
     * @returns {Promise<string>} Base64 audio data URL.
     */
    window.recordAudio = function (duration) {
        if (duration === undefined || duration === null) duration = 5;
        duration = Math.max(0.5, Number(duration));

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            return Promise.reject(new Error('[Audio] getUserMedia is not supported'));
        }

        return navigator.mediaDevices.getUserMedia({ audio: true, video: false })
            .then(function (stream) {
                return new Promise(function (resolve, reject) {
                    var chunks = [];
                    var recorder = new MediaRecorder(stream);

                    recorder.ondataavailable = function (e) {
                        if (e.data && e.data.size > 0) chunks.push(e.data);
                    };

                    recorder.onstop = function () {
                        stream.getTracks().forEach(function (t) { t.stop(); });
                        var blob = new Blob(chunks, { type: recorder.mimeType });
                        var reader = new FileReader();
                        reader.onloadend = function () { resolve(reader.result); };
                        reader.onerror  = reject;
                        reader.readAsDataURL(blob);
                    };

                    recorder.onerror = function (e) {
                        stream.getTracks().forEach(function (t) { t.stop(); });
                        reject(e.error || e);
                    };

                    recorder.start();
                    setTimeout(function () {
                        if (recorder.state !== 'inactive') recorder.stop();
                    }, duration * 1000);
                });
            });
    };

    console.log('[Audio] Plugin ready');
})();
