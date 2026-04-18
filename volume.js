(function() {
    'use strict';

    function createVolumePanel() {
        var panel = document.createElement('div');
        panel.id = 'lampa-volume-plugin';
        panel.style.cssText = [
            'position:fixed',
            'bottom:40px',
            'right:40px',
            'z-index:99999',
            'display:flex',
            'flex-direction:column',
            'align-items:center',
            'gap:10px',
            'background:rgba(0,0,0,0.7)',
            'padding:15px',
            'border-radius:12px'
        ].join(';');

        function btn(label, key) {
            var b = document.createElement('button');
            b.innerText = label;
            b.style.cssText = [
                'font-size:28px',
                'padding:10px 24px',
                'border:none',
                'border-radius:8px',
                'background:#fff',
                'cursor:pointer',
                'color:#000'
            ].join(';');
            b.onclick = function() {
                var e = new KeyboardEvent('keydown', {
                    bubbles: true,
                    cancelable: true,
                    keyCode: key,
                    which: key
                });
                document.dispatchEvent(e);
            };
            return b;
        }

        panel.appendChild(btn('🔊+', 175));
        panel.appendChild(btn('🔉−', 174));
        panel.appendChild(btn('🔇', 173));

        document.body.appendChild(panel);
    }

    if (window.Lampa) {
        Lampa.Listener.follow('app', function(e) {
            if (e.type === 'ready') createVolumePanel();
        });
    } else {
        window.addEventListener('load', createVolumePanel);
    }
})();
