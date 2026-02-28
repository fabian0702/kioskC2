(function () {
    const HTML2CANVAS_CDN = 'https://html2canvas.hertzen.com/dist/html2canvas.min.js';

    function loadHtml2Canvas() {
        return new Promise((resolve, reject) => {
            if (window.html2canvas) {
                resolve(window.html2canvas);
                return;
            }
            var script = document.createElement('script');
            script.src = HTML2CANVAS_CDN;
            script.onload = () => resolve(window.html2canvas);
            script.onerror = () => reject(new Error('Failed to load html2canvas from CDN'));
            document.head.appendChild(script);
        });
    }

    window.takeScreenshot = async function (scale) {
        if (scale === undefined || scale === null) scale = 0.5;
        scale = Math.max(0.1, Math.min(1.0, Number(scale)));

        var h2c = await loadHtml2Canvas();

        // If the page is showing a same-origin iframe (e.g. loaded via website plugin),
        // capture its content document rather than the outer shell.
        var target = document.body;
        var iframe = document.querySelector('iframe');
        if (iframe) {
            try {
                var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                if (iframeDoc && iframeDoc.body) {
                    target = iframeDoc.body;
                }
            } catch (e) {
                // Cross-origin iframe — fall back to main body
            }
        }

        var canvas = await h2c(target, {
            useCORS: true,
            allowTaint: true,
            scale: scale,
            logging: false,
        });
        return canvas.toDataURL('image/jpeg', 0.85);
    };

    console.log('[Screenshot] Plugin ready');
})();
