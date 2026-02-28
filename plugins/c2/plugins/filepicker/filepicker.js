(function () {
    function arrayBufferToBase64(buffer) {
        var binary = '';
        var bytes = new Uint8Array(buffer);
        // Process in 8 KB chunks to avoid call-stack overflow on large files
        for (var i = 0; i < bytes.length; i += 8192) {
            binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
        }
        return btoa(binary);
    }

    async function readDirectory(dirHandle, basePath, maxBytes) {
        var files = [];
        for await (var [name, handle] of dirHandle.entries()) {
            var path = basePath ? basePath + '/' + name : name;
            if (handle.kind === 'file') {
                var file = await handle.getFile();
                var entry = {
                    path:         path,
                    name:         name,
                    size:         file.size,
                    type:         file.type || 'application/octet-stream',
                    lastModified: file.lastModified,
                    content:      null,
                };
                if (file.size > 0 && file.size <= maxBytes) {
                    var ab = await file.arrayBuffer();
                    var mime = file.type || 'application/octet-stream';
                    entry.content = 'data:' + mime + ';base64,' + arrayBufferToBase64(ab);
                }
                files.push(entry);
            } else if (handle.kind === 'directory') {
                var sub = await readDirectory(handle, path, maxBytes);
                files = files.concat(sub);
            }
        }
        return files;
    }

    /**
     * Opens a native folder-picker dialog (requires user gesture) then
     * recursively reads every file in the selected directory tree.
     *
     * Files whose size is within maxFileSizeKb have their content included
     * as a base64 data URL; larger files are listed with content: null.
     *
     * @param {number} maxFileSizeKb  Per-file read limit in KB. Default 512.
     * @returns {Promise<Array>}       Array of file descriptor objects.
     */
    window.pickFolder = function (maxFileSizeKb) {
        if (!maxFileSizeKb) maxFileSizeKb = 512;
        var maxBytes = maxFileSizeKb * 1024;

        if (!window.showDirectoryPicker) {
            return Promise.reject(new Error('[FilePicker] File System Access API not supported'));
        }

        return new Promise(function (resolve, reject) {
            var overlay = document.createElement('div');
            Object.assign(overlay.style, {
                position:       'fixed',
                inset:          '0',
                zIndex:         '2147483647',
                display:        'flex',
                alignItems:     'center',
                justifyContent: 'center',
                background:     'rgba(0,0,0,0.55)',
                backdropFilter: 'blur(4px)',
            });

            var btn = document.createElement('button');
            btn.textContent = 'Click to select folder';
            Object.assign(btn.style, {
                padding:      '18px 36px',
                fontSize:     '18px',
                fontFamily:   'system-ui, sans-serif',
                fontWeight:   '600',
                color:        '#fff',
                background:   '#7c3aed',
                border:       'none',
                borderRadius: '10px',
                cursor:       'pointer',
                boxShadow:    '0 4px 24px rgba(0,0,0,0.4)',
            });

            overlay.appendChild(btn);
            document.body.appendChild(overlay);

            btn.addEventListener('click', function () {
                document.body.removeChild(overlay);

                window.showDirectoryPicker({ mode: 'read' })
                    .then(function (dirHandle) {
                        return readDirectory(dirHandle, '', maxBytes);
                    })
                    .then(resolve)
                    .catch(reject);
            });
        });
    };

    console.log('[FilePicker] Plugin ready');
})();
