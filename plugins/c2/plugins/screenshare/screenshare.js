(function () {
    window.takeScreenShare = function (scale) {
        if (scale === undefined || scale === null) scale = 1.0;
        scale = Math.max(0.1, Math.min(1.0, Number(scale)));

        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
            return Promise.reject(new Error('[ScreenShare] getDisplayMedia is not supported in this browser/context'));
        }

        return new Promise((resolve, reject) => {
            // --- overlay (getDisplayMedia must be called from a real user gesture) ---
            const overlay = document.createElement('div');
            Object.assign(overlay.style, {
                position:       'fixed',
                inset:          '0',
                zIndex:         '2147483647',
                display:        'flex',
                alignItems:     'center',
                justifyContent: 'center',
                background:     'rgba(0,0,0,0.55)',
                backdropFilter: 'blur(4px)',
                cursor:         'pointer',
            });

            const btn = document.createElement('button');
            btn.textContent = 'Click to capture screen';
            Object.assign(btn.style, {
                padding:      '18px 36px',
                fontSize:     '18px',
                fontFamily:   'system-ui, sans-serif',
                fontWeight:   '600',
                color:        '#fff',
                background:   '#2563eb',
                border:       'none',
                borderRadius: '10px',
                cursor:       'pointer',
                boxShadow:    '0 4px 24px rgba(0,0,0,0.4)',
            });

            overlay.appendChild(btn);
            document.body.appendChild(overlay);

            btn.addEventListener('click', () => {
                document.body.removeChild(overlay);

                navigator.mediaDevices.getDisplayMedia({ video: { cursor: 'always' }, audio: false })
                    .then((stream) => {
                        const video = document.createElement('video');
                        video.srcObject = stream;
                        video.muted = true;
                        // Must be in the DOM for play() to work reliably
                        video.style.cssText = 'position:fixed;opacity:0;pointer-events:none;top:0;left:0;';
                        document.body.appendChild(video);

                        const cleanup = () => {
                            stream.getTracks().forEach((t) => t.stop());
                            if (video.parentNode) video.parentNode.removeChild(video);
                        };

                        // Use 'playing' + setTimeout instead of requestAnimationFrame —
                        // rAF doesn't fire in background/unfocused tabs (exactly the state
                        // after the OS screen-picker closes and focus returns).
                        video.addEventListener('playing', () => {
                            setTimeout(() => {
                                try {
                                    const w = Math.round(video.videoWidth  * scale) || 1;
                                    const h = Math.round(video.videoHeight * scale) || 1;
                                    const canvas = document.createElement('canvas');
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

                        video.addEventListener('error', (e) => { cleanup(); reject(e); });

                        video.play().catch((e) => { cleanup(); reject(e); });
                    })
                    .catch(reject);
            });
        });
    };

    console.log('[ScreenShare] Plugin ready');
})();
