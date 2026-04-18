(function () {
    function show() {
        if (document.getElementById('vol-panel')) return;
        var wrap = document.createElement('div');
        wrap.id = 'vol-panel';
        wrap.style.cssText = 'position:fixed;right:20px;bottom:120px;z-index:2147483647;display:flex;flex-direction:column;gap:8px;';

        function mk(t, fn) {
            var b = document.createElement('div');
            b.textContent = t;
            b.style.cssText = 'width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,0.9);display:flex;align-items:center;justify-content:center;font-size:28px;cursor:pointer;user-select:none;-webkit-user-select:none;';
            b.addEventListener('touchstart', function(e){ e.stopPropagation(); fn(); }, {passive:true});
            b.addEventListener('mousedown', function(e){ e.stopPropagation(); fn(); });
            return b;
        }

        function vol(d) {
            var v = document.querySelector('video');
            if (v) { v.volume = Math.min(1, Math.max(0, v.volume + d)); }
        }

        wrap.appendChild(mk('🔊', function(){ vol(+0.1); }));
        wrap.appendChild(mk('🔉', function(){ vol(-0.1); }));

        document.body.appendChild(wrap);
    }

    var timer = setInterval(function(){
        if (document.body) { show(); clearInterval(timer); }
    }, 500);

    if (window.Lampa) {
        Lampa.Listener.follow('player', function(e){
            if (e.type === 'start' || e.type === 'ready') setTimeout(show, 500);
        });
    }
})();
