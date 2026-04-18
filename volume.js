(function() {
    'use strict';

    function addVolumeButtons() {
        if (document.getElementById('lampa-volume-plugin')) return;

        var panel = document.createElement('div');
        panel.id = 'lampa-volume-plugin';
        panel.style.cssText = 'position:fixed;bottom:40px;right:40px;z-index:99999;display:flex;flex-direction:column;align-items:center;gap:10px;background:rgba(0,0,0,0.8);padding:15px;border-radius:12px';

        function btn(label, action) {
            var b = document.createElement('button');
            b.innerText = label;
            b.style.cssText = 'font-size:32px;width:70px;height:70px;border:none;border-radius:50%;background:#fff;cursor:pointer;color:#000';
            b.onclick = action;
            return b;
        }

        panel.appendChild(btn('🔊', function() {
            var e = new KeyboardEvent('keydown', {bubbles:true, keyCode:175, which:175});
            document.dispatchEvent(e);
        }));
        panel.appendChild(btn('🔉', function() {
            var e = new KeyboardEvent('keydown', {bubbles:true, keyCode:174, which:174});
            document.dispatchEvent(e);
        }));
        panel.appendChild(btn('🔇', function() {
            var e = new KeyboardEvent('keydown', {bubbles:true, keyCode:173, which:173});
            document.dispatchEvent(e);
        }));

        document.body.appendChild(panel);
    }

    setTimeout(addVolumeButtons, 3000);
    document.addEventListener('click', addVolumeButtons);
})();
