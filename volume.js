(function() {
    'use strict';

    function addVolumeButtons() {
        if (document.getElementById('vol-panel')) return;

        var panel = document.createElement('div');
        panel.id = 'vol-panel';
        panel.style.cssText = 'position:fixed;bottom:40px;right:40px;z-index:2147483647;display:flex;flex-direction:column;gap:12px';

        function btn(label, action) {
            var b = document.createElement('button');
            b.innerText = label;
            b.style.cssText = 'font-size:36px;width:80px;height:80px;border:none;border-radius:50%;background:rgba(255,255,255,0.9);cursor:pointer';
            b.addEventListener('click', function(e) {
                e.stopPropagation();
                action();
            });
            return b;
        }

        panel.appendChild(btn('🔊', function() {
            if (window.Lampa && Lampa.Volume) {
                Lampa.Volume.up();
            } else if (window.Android && Android.volumeUp) {
                Android.volumeUp();
            } else {
                var v = document.querySelector('video');
                if (v) v.volume = Math.min(1, v.volume + 0.1);
            }
        }));

        panel.appendChild(btn('🔉', function() {
            if (window.Lampa && Lampa.Volume) {
                Lampa.Volume.down();
            } else if (window.Android && Android.volumeDown) {
                Android.volumeDown();
            } else {
                var v = document.querySelector('video');
                if (v) v.volume = Math.max(0, v.volume - 0.1);
            }
        }));

        document.body.appendChild(panel);
    }

    setTimeout(addVolumeButtons, 2000);
})();
