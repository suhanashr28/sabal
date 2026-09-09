(() => {
  const read = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } };
  const write = (key, value) => localStorage.setItem(key, JSON.stringify(value));
  const names = { my: 'My Profile', sabal: 'Sabal' };
  let profile = read('lf-profile', 'sabal');
  if (!names[profile]) profile = 'sabal';
  const requested = new URLSearchParams(location.search).get('profile');
  if (names[requested]) { profile = requested; write('lf-profile', profile); }
  const favoriteKey = () => `lf-favorites-${profile}`;
  const favorites = () => read(favoriteKey(), []);
  const el = (tag, text, cls) => { const node = document.createElement(tag); if (text) node.textContent = text; if (cls) node.className = cls; return node; };
  function heart(item) {
    const button = el('button', '', 'lf-heart'); button.type = 'button'; button.dataset.loveId = item.id;
    const sync = () => { const saved = favorites().some(x => x.id === item.id); button.textContent = saved ? '♥ Loved' : '♡ Love'; button.setAttribute('aria-pressed', String(saved)); button.setAttribute('aria-label', `${saved ? 'Remove from' : 'Add to'} favorites: ${item.title}`); };
    button.addEventListener('click', event => { event.preventDefault(); event.stopPropagation(); let items = favorites(); items = items.some(x => x.id === item.id) ? items.filter(x => x.id !== item.id) : [...items, item]; try { write(favoriteKey(), items); document.dispatchEvent(new Event('favorites-change')); } catch { alert('Unable to save favorites. Please check browser storage.'); } });
    document.addEventListener('favorites-change', sync); sync(); return button;
  }
  function renderFavorites() {
    const grid = document.querySelector('#saved-favorites'); if (!grid) return;
    grid.replaceChildren(); const items = favorites(); document.querySelector('#favorites-empty').hidden = items.length > 0;
    items.forEach(item => { const card = el('article', '', 'lf-card'); const link = el('a'); link.href = item.href; if (item.image) { const img = el('img'); img.src = item.image; img.alt = item.title; link.append(img); } link.append(el('h2', item.title)); card.append(link, heart(item)); grid.append(card); });
  }
  document.addEventListener('favorites-change', renderFavorites); renderFavorites();
  document.querySelectorAll('.profile-card').forEach(card => { const id = new URL(card.href).searchParams.get('profile'); card.addEventListener('click', () => write('lf-profile', id)); const pic = read(`lf-picture-${id}`, ''); if(pic) { const img = el('img'); img.src = pic; img.alt = names[id]; card.querySelector('.avatar').replaceChildren(img); } });
  function renderProfile() {
    const picture = read(`lf-picture-${profile}`, '');
    document.querySelectorAll('.mini-profile').forEach(node => { node.replaceChildren(); node.setAttribute('aria-label', `${names[profile]}: switch profile`); if(picture) { const img = el('img'); img.src = picture; img.alt = names[profile]; node.append(img); } else node.textContent = names[profile][0]; });
    const preview = document.querySelector('#profile-preview'); if(preview) { preview.hidden = !picture; if(picture) preview.src = picture; else preview.removeAttribute('src'); const initial = document.querySelector('#profile-initial'); initial.hidden = !!picture; initial.textContent = names[profile][0]; }
  }
  renderProfile();
  const select = document.querySelector('#profile-select');
  if(select) {
    select.value = profile; select.addEventListener('change', () => { profile = select.value; write('lf-profile', profile); renderProfile(); document.querySelector('#profile-picture').value = ''; document.querySelector('#profile-status').textContent = `Switched to ${names[profile]}.`; });
    document.querySelector('#remove-picture').addEventListener('click', () => { localStorage.removeItem(`lf-picture-${profile}`); renderProfile(); document.querySelector('#profile-status').textContent = 'Profile picture reset.'; });
    document.querySelector('#profile-picture').addEventListener('change', async event => {
      const file = event.target.files[0]; if(!file) return; const targetProfile = profile; const status = document.querySelector('#profile-status');
      try { if(!file.type.startsWith('image/')) throw Error('Choose an image file.'); const bitmap = await createImageBitmap(file); const canvas = document.createElement('canvas'); canvas.width = canvas.height = 256; const size = Math.min(bitmap.width, bitmap.height); canvas.getContext('2d').drawImage(bitmap, (bitmap.width-size)/2, (bitmap.height-size)/2, size, size, 0, 0, 256, 256); bitmap.close(); write(`lf-picture-${targetProfile}`, canvas.toDataURL('image/jpeg', .85)); renderProfile(); status.textContent = `Picture saved for ${names[targetProfile]}.`; } catch { status.textContent = 'Could not save this image. Try a JPG or PNG and allow browser storage.'; }
    });
  }
  if(!document.querySelector('#saved-favorites')) {
    document.querySelectorAll('main img').forEach(img => {
      if(!img.getAttribute('src') || img.id === 'profile-preview' || img.closest('.profile-card, dialog, a')) return;
      const src = img.getAttribute('src'); const wrapper = el('div', '', 'lf-photo'); img.parentNode.insertBefore(wrapper, img); wrapper.append(img, heart({id:`photo:${src}`, title:img.alt || 'Our photo', image:src, href:src}));
    });
    document.querySelectorAll('.memory-card').forEach(card => { const title = card.querySelector('strong')?.textContent || 'Our memory'; const href = card.getAttribute('href'); const wrap = el('div', '', 'lf-memory'); card.parentNode.insertBefore(wrap, card); wrap.append(card, heart({id:`memory:${href}`, title, href, image:card.querySelector('img')?.getAttribute('src')})); });
    if(!['home.html','settings.html','profile.html','watch.html','login.html','index.html'].includes(location.pathname.split('/').pop())) {
      const heading = document.querySelector('main h1'); if(heading) { const href = location.pathname.split('/').pop()+location.search; heading.after(heart({id:`page:${href}`,title:heading.textContent,href})); }
    }
  }
  const videoGrid = document.querySelector('#video-grid');
  if(videoGrid) {
    let dbPromise;
    function database() { return dbPromise ||= new Promise((resolve,reject) => { const request = indexedDB.open('loveflix-videos',1); request.onupgradeneeded = () => request.result.createObjectStore('videos'); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error); }); }
    async function storage(mode, id, file) { const db = await database(); return new Promise((resolve,reject) => { const tx = db.transaction('videos', mode); const store = tx.objectStore('videos'); const req = mode === 'readonly' ? store.get(id) : store.put(file,id); tx.oncomplete = () => resolve(req.result); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error); }); }
    ['Birthday Celebration','Our First Date','Our Story Begins','The Best Part','Family Moments','Our Adventures'].forEach((title,index) => {
      const id = `video-${index+1}`; const card = el('article','','lf-card'); card.id = id; const video = el('video'); video.controls = true; video.preload = 'metadata'; video.poster = `images/us-${index+2}.jpeg`; video.setAttribute('aria-label',title); const status = el('p','No video added yet.'); const label = el('label','Choose video'); label.htmlFor = `upload-${id}`; const input = el('input'); input.type = 'file'; input.accept = 'video/*'; input.id = label.htmlFor;
      let url; function playFile(file) { if(url) URL.revokeObjectURL(url); url = URL.createObjectURL(file); video.src = url; status.textContent = file.name; }
      if(index === 0) { video.src = 'birthday.mp4'; video.poster = 'images/birthday-01.jpeg'; status.textContent = 'Birthday Celebration'; }
      storage('readonly',id).then(file => { if(file) playFile(file); }).catch(() => { status.textContent = 'Video storage is unavailable in this browser.'; });
      input.addEventListener('change',async () => { const file = input.files[0]; if(!file) return; if(!file.type.startsWith('video/')) { status.textContent = 'Please choose a video file.'; return; } try { await storage('readwrite',id,file); playFile(file); } catch { status.textContent = 'Could not save video. Try a smaller file or allow browser storage.'; } });
      video.addEventListener('error',() => { status.textContent = 'This video cannot play. Try an MP4 encoded with H.264.'; });
      card.append(video,el('h2',title),heart({id,title,href:`watch.html#${id}`,image:video.poster}),status,label,input); videoGrid.append(card);
    });
  }
  window.addEventListener('storage', () => { document.dispatchEvent(new Event('favorites-change')); });
})();
