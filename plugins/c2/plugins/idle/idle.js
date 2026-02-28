(function () {
    if (window._idleTracking) return; // already installed
    window._idleTracking = true;
    window._idleLastActivity = Date.now();

    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'wheel'].forEach(function (evt) {
        window.addEventListener(evt, function () {
            window._idleLastActivity = Date.now();
        }, { passive: true, capture: true });
    });

    window.getIdleTime = function () {
        return (Date.now() - window._idleLastActivity) / 1000;
    };

    window.resetIdleTime = function () {
        window._idleLastActivity = Date.now();
    };

    console.log('[Idle] Plugin ready');
})();
