window.createLoveFlixPlayer = (root = document) => {
 const $ = id => root.querySelector(`#${id}`);
 const player = $('player'), movie = $('movie'), seek = $('seek'), center = $('center-play'), toggle = $('toggle'), status = $('status');
 let timer;
 const format = seconds => `${Math.floor((seconds || 0) / 60)}:${String(Math.floor((seconds || 0) % 60)).padStart(2, '0')}`;
 function wake() { player.classList.remove('idle'); clearTimeout(timer); if (!movie.paused) timer = setTimeout(() => { if (!player.contains(root.activeElement) || root.activeElement === movie) player.classList.add('idle'); }, 3000); }
 async function play() { try { await movie.play(); status.textContent = ''; } catch { status.textContent = 'Press play to start your movie.'; center.hidden = false; wake(); } }
 function switchPlayback() { movie.paused ? play() : movie.pause(); }
 async function fullscreen() { try { if (document.fullscreenElement) await document.exitFullscreen(); else if (player.requestFullscreen) await player.requestFullscreen(); else if (movie.webkitEnterFullscreen) movie.webkitEnterFullscreen(); } catch { status.textContent = 'Fullscreen is unavailable. You can still watch here.'; } }
 center.onclick = () => { play(); if (!document.fullscreenElement) fullscreen(); };
 toggle.onclick = switchPlayback;
 movie.onclick = switchPlayback;
 $('back').onclick = () => { movie.currentTime = Math.max(0, movie.currentTime - 10); wake(); };
 $('forward').onclick = () => { movie.currentTime = Math.min(movie.duration || 0, movie.currentTime + 10); wake(); };
 $('mute').onclick = () => { movie.muted = !movie.muted; };
 movie.addEventListener('volumechange', () => { $('mute').textContent = movie.muted ? '×♪' : '♪'; $('mute').setAttribute('aria-label', movie.muted ? 'Unmute' : 'Mute'); });
 $('fullscreen').onclick = fullscreen;
 document.addEventListener('fullscreenchange', () => $('fullscreen').setAttribute('aria-label', document.fullscreenElement ? 'Exit fullscreen' : 'Enter fullscreen'));
 seek.addEventListener('input', () => { if (Number.isFinite(movie.duration)) movie.currentTime = Number(seek.value); wake(); });
 movie.addEventListener('loadedmetadata', () => { seek.max = movie.duration; $('duration').textContent = format(movie.duration); });
 movie.addEventListener('timeupdate', () => { seek.value = movie.currentTime; $('elapsed').textContent = format(movie.currentTime); seek.setAttribute('aria-valuetext', `${format(movie.currentTime)} of ${format(movie.duration)}`); });
 for (const event of ['play', 'pause', 'ended']) movie.addEventListener(event, () => { center.hidden = !movie.paused; toggle.textContent = movie.paused ? '▶' : 'Ⅱ'; toggle.setAttribute('aria-label', movie.paused ? 'Play' : 'Pause'); wake(); });
 movie.addEventListener('waiting', () => { status.textContent = 'Loading your movie…'; });
 movie.addEventListener('playing', () => { status.textContent = ''; });
 movie.addEventListener('error', () => { status.textContent = 'The movie could not load. Please reload and try again.'; wake(); });
 for (const event of ['pointermove', 'pointerdown', 'focusin']) player.addEventListener(event, wake);
 document.addEventListener('keydown', event => { if (!player.getClientRects().length || event.composedPath()[0].matches('input,button,a')) return; if ([' ', 'ArrowLeft', 'ArrowRight', 'f', 'm'].includes(event.key)) event.preventDefault(); if (event.key === ' ') switchPlayback(); if (event.key === 'ArrowLeft') $('back').click(); if (event.key === 'ArrowRight') $('forward').click(); if (event.key === 'f') fullscreen(); if (event.key === 'm') $('mute').click(); wake(); });
 return { play, pause: () => movie.pause(), fullscreen, wake };
};
if (document.getElementById('player')) window.createLoveFlixPlayer().play();
