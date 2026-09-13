(() => {
 const link = document.querySelector('.play-btn');
 if (!link) return;
 const host = document.createElement('dialog');
 host.setAttribute('aria-label', 'Happy Birthday Baby movie');
 host.style.cssText = 'position:fixed;inset:0;width:100vw;max-width:none;height:100dvh;max-height:none;margin:0;padding:0;border:0;background:black;color:white;overflow:hidden';
 const surface = document.createElement('div'); host.append(surface);
 const root = surface.attachShadow({mode:'open'});
 root.innerHTML = "<style>*{box-sizing:border-box}body{margin:0;background:#000;color:#fff;font-family:Arial,Helvetica,sans-serif}#player{position:relative;width:100%;height:100vh;height:100dvh;overflow:hidden;background:#000}video{width:100%;height:100%;object-fit:contain}header,footer{position:absolute;left:0;width:100%;padding:28px 4%;transition:opacity .25s}header{top:0;display:flex;align-items:center;gap:25px;background:linear-gradient(#000b,transparent)}header a{color:white;text-decoration:none;font-size:36px;padding:8px}.brand{font-size:11px;letter-spacing:3px;color:#e50914;font-weight:800}h1{font-size:20px;font-weight:500;margin:8px 0}footer{bottom:0;padding-bottom:max(24px,env(safe-area-inset-bottom));background:linear-gradient(transparent,#000d)}button{border:0;background:transparent;color:#fff;cursor:pointer;font-size:30px;min-width:48px;min-height:48px;border-radius:5px}button:hover{background:#ffffff24}button:focus-visible,a:focus-visible,input:focus-visible{outline:2px solid white;outline-offset:4px}.center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);border:2px solid #ffffff80;border-radius:50%;width:86px;height:86px;background:#0006;font-size:38px}.center[hidden]{display:none}.timeline{display:flex;align-items:center;gap:15px;font-size:13px;font-variant-numeric:tabular-nums}input{flex:1;min-width:0;accent-color:#e50914;cursor:pointer}.controls{display:flex;align-items:center;gap:18px;margin-top:13px}.controls button{position:relative}.controls small{position:absolute;left:0;right:0;top:23px;font-size:10px}.movie-title{flex:1;font-size:15px}#fullscreen{margin-left:auto}#status{position:absolute;top:62%;left:10%;width:80%;text-align:center;font-size:15px}.idle .chrome{opacity:0;pointer-events:none}.idle{cursor:none}@media(max-width:600px){header,footer{padding-left:18px;padding-right:18px}h1{font-size:16px}.controls{gap:8px}.movie-title{font-size:12px}.brand{font-size:9px}.center{width:72px;height:72px}}@media(prefers-reduced-motion:reduce){.chrome{transition:none}}\n</style>\n<main id=\"player\" aria-label=\"Happy Birthday Baby movie player\">\n <video id=\"movie\" playsinline preload=\"metadata\" aria-label=\"Happy Birthday Baby\" src=\"play/birthday-film.mp4\"></video>\n <header class=\"chrome\"><a href=\"home.html\" aria-label=\"Back to Home\">\u2190</a><div><span class=\"brand\">LOVEFLIX ORIGINAL</span><h1>Happy Birthday Baby</h1></div></header>\n <button id=\"center-play\" class=\"center\" aria-label=\"Play movie\">\u25b6</button>\n <p id=\"status\" role=\"status\"></p>\n <footer class=\"chrome\">\n  <div class=\"timeline\"><span id=\"elapsed\">0:00</span><input id=\"seek\" type=\"range\" min=\"0\" max=\"100\" value=\"0\" step=\"0.1\" aria-label=\"Seek through movie\"><span id=\"duration\">0:00</span></div>\n  <div class=\"controls\"><button id=\"toggle\" aria-label=\"Play\">\u25b6</button><button id=\"back\" aria-label=\"Rewind 10 seconds\">\u21b6<small>10</small></button><button id=\"forward\" aria-label=\"Forward 10 seconds\">\u21b7<small>10</small></button><button id=\"mute\" aria-label=\"Mute\">\u266a</button><span class=\"movie-title\">Happy Birthday Baby</span><button id=\"fullscreen\" aria-label=\"Enter fullscreen\">\u26f6</button></div>\n </footer>\n</main>\n";
 document.body.append(host);
 const moviePlayer = window.createLoveFlixPlayer(root);
 window.setLoveFlixMovie = url => { const video=root.querySelector('video'); if (url && video.getAttribute('src') !== url) video.src=url; if (!url) {video.pause();video.removeAttribute('src');video.load();} link.dataset.unavailable=String(!url); };
 if (window.LF?.state) {const film=LF.media('play-movie');window.setLoveFlixMovie(film&&!film.deleted?film.url:null);}
 let previousOverflow;
 function closeMovie() {
  moviePlayer.pause();
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  host.close(); document.body.style.overflow = previousOverflow; link.focus();
 }
 root.querySelector('header a').addEventListener('click', event => { event.preventDefault(); closeMovie(); });
 host.addEventListener('cancel', event => { event.preventDefault(); closeMovie(); });
 link.addEventListener('click', event => {
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault(); if (link.dataset.unavailable==='true') {window.LF?.notify('Restore the Play movie in Settings to watch it.');return;} previousOverflow = document.body.style.overflow;
  document.body.style.overflow = 'hidden'; host.showModal(); root.activeElement?.blur();
  moviePlayer.play(); moviePlayer.fullscreen(); moviePlayer.wake();
 });
})();
