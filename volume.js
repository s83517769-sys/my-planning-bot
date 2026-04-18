// Lampa plugin
var PLUGIN_NAME = 'volume_control';

(function () {
    function show() {
        if (document.getElementById('vol-panel')) return;
        var wrap = document.createElement('div');
        wrap.id = 'vol-panel';
        wrap.style.cssText = 'position:fixed;right:20px;bottom:120px;z-index:2147483647;display:flex;flex-direction:column;gap:8px;';

        function mk(t, fn) {
            var b = document.createElement('div');
            b.textContent = t;
            b.style.cssText = 'width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,0.9);display:flex;align-items:center;justify-content:center;font-size:28px;cursor:pointer;';
            b.addEventListener('touchstart', function(e){ e.stopPropagation(); fn(); }, {passive:true});
            b.addEventListener('click', function(e){ e.stopPropagation(); fn(); });
            return b;
        }

        function vol(d) {
            var v = document.querySelector('video');
            if (v) v.volume = Math.min(1, Math.max(0, v.volume + d));
        }

        wrap.appendChild(mk('🔊', function(){ vol(+0.1); }));
        wrap.appendChild(mk('🔉', function(){ vol(-0.1); }));
        document.body.appendChild(wrap);
    }

    Lampa.Listener.follow('app', function(e){
        if (e.type === 'ready') show();
    });

    setTimeout(show, 2000);
})();
