(function () {
    /**
     * Captures a photo from the user's camera via getUserMedia.
     *
     * Unlike getDisplayMedia, getUserMedia does not require a user gesture —
     * the browser shows its own permission prompt automatically.
     *
     * @param {string} facing  - "user" (front cam) or "environment" (rear cam). Default "user".
     * @param {number} scale   - Resolution scale factor (0.1–1.0). Default 1.0.
     * @returns {Promise<string>} Base64-encoded JPEG data URL.
     */
    window.takePhoto = function (facing, scale) {
        if (!facing) facing = 'user';
        if (scale === undefined || scale === null) scale = 1.0;
        scale = Math.max(0.1, Math.min(1.0, Number(scale)));

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            return Promise.reject(new Error('[Camera] getUserMedia is not supported in this browser/context'));
        }

        return navigator.mediaDevices.getUserMedia({ video: { facingMode: facing }, audio: false })
            .then(function (stream) {
                return new Promise(function (resolve, reject) {
                    var video = document.createElement('video');
                    video.srcObject = stream;
                    video.muted = true;
                    video.style.cssText = 'position:fixed;opacity:0;pointer-events:none;top:0;left:0;';
                    document.body.appendChild(video);

                    var cleanup = function () {
                        stream.getTracks().forEach(function (t) { t.stop(); });
                        if (video.parentNode) video.parentNode.removeChild(video);
                    };

                    video.addEventListener('playing', function () {
                        setTimeout(function () {
                            try {
                                var w = Math.round(video.videoWidth  * scale) || 1;
                                var h = Math.round(video.videoHeight * scale) || 1;
                                var canvas = document.createElement('canvas');
                                canvas.width  = w;
                                canvas.height = h;
                                canvas.getContext('2d').drawImage(video, 0, 0, w, h);
                                cleanup();
                                resolve(canvas.toDataURL('image/jpeg', 0.85));
                            } catch (e) {
                                cleanup();
                                reject(e);
                            }
                        }, 300);
                    });

                    video.addEventListener('error', function (e) { cleanup(); reject(e); });

                    video.play().catch(function (e) { cleanup(); reject(e); });
                });
            });
    };

    console.log('[Camera] Plugin ready');
})();
