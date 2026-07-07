(function () {
    'use strict';

    function protectVideo(video) {
        if (!video || video.dataset.protectedApplied === '1') return;
        video.dataset.protectedApplied = '1';
        video.setAttribute('controlsList', 'nodownload noremoteplayback');
        video.setAttribute('disablePictureInPicture', '');
        video.setAttribute('disableRemotePlayback', '');
        video.addEventListener('contextmenu', function (e) {
            e.preventDefault();
        });
        video.addEventListener('dragstart', function (e) {
            e.preventDefault();
        });
    }

    function init() {
        document.querySelectorAll('video.protected-video, video[data-protected="1"]').forEach(protectVideo);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
