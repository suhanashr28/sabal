(() => {
 const LF = window.LF = {};
 LF.el = (tag, text = '', cls = '') => { const el = document.createElement(tag); el.textContent = text; el.className = cls; return el; };
 LF.profile = () => { const requested = new URLSearchParams(location.search).get('profile'); const saved = localStorage.getItem('lf-active-profile'); const value = ['my','sabal'].includes(requested) ? requested : ['my','sabal'].includes(saved) ? saved : 'sabal'; localStorage.setItem('lf-active-profile', value); return value; };
 LF.api = async (path, options = {}) => {
  const response = await fetch(path, {credentials:'same-origin', ...options, headers: {...(options.body && typeof options.body === 'string' ? {'Content-Type':'application/json'} : {}), ...options.headers}});
  const data = await response.json().catch(() => ({error:'The local server did not respond correctly.'}));
  if (!response.ok) { if (response.status === 401 && !path.endsWith('/login')) location.href = '/login.html'; throw Error(data.error || 'Could not save your change.'); }
  return data;
 };
 LF.save = (path, method, data) => LF.api(path, {method, body: JSON.stringify(data)});
 LF.notify = message => { let box = document.getElementById('lf-notice'); if (!box) { box = LF.el('div','','lf-notice'); box.id='lf-notice'; box.setAttribute('role','status'); document.body.append(box); } box.textContent=message; clearTimeout(LF.noticeTimer); LF.noticeTimer=setTimeout(() => box.remove(),6000); };
 LF.upload = (file, collection, id, progress) => new Promise((resolve,reject) => {
  const request = new XMLHttpRequest(); request.open('POST', id ? `/api/media/${id}/file` : '/api/media');
  request.setRequestHeader('X-File-Name',encodeURIComponent(file.name)); request.setRequestHeader('X-Collection',collection); request.setRequestHeader('Content-Type',file.type || 'application/octet-stream');
  request.upload.onprogress=event => { if (event.lengthComputable && progress) progress(Math.round(event.loaded/event.total*100)); };
  request.onerror=() => reject(Error('Upload interrupted. Check that the server is running.'));
  request.onload=() => { try { const result=JSON.parse(request.responseText); request.status<300 ? resolve(result) : reject(Error(result.error)); } catch { reject(Error('Upload failed. Please try again.')); } }; request.send(file);
 });
 const localUpload=LF.upload;
 LF.upload=async(file,collection,id,progress)=>{
  if(!LF.state?.directUploads)return localUpload(file,collection,id,progress);
  const prepared=await LF.save('/api/uploads/prepare','POST',{name:file.name,size:file.size,collection,id:id||''});
  await new Promise((resolve,reject)=>{const request=new XMLHttpRequest();request.open('PUT',prepared.url);request.setRequestHeader('Content-Type',prepared.contentType);request.upload.onprogress=e=>{if(e.lengthComputable&&progress)progress(Math.round(e.loaded/e.total*100));};request.onerror=()=>reject(Error('Upload interrupted. Please try again.'));request.onload=()=>request.status>=200&&request.status<300?resolve():reject(Error('Storage could not accept this file. Please try again.'));request.send(file);});
  return LF.save('/api/uploads/complete','POST',{id:prepared.id});
 };
 LF.refresh = async () => { LF.state=await LF.api('/api/state'); LF.state.media.forEach(item=>{item.sourceUrl=item.url;item.url=item.displayUrl||item.url;}); document.dispatchEvent(new Event('lf-state')); return LF.state; };
 LF.media = id => LF.state.media.find(item => item.id===id);
 LF.favorite = item => {
  if(item.id.startsWith('media:'))item={...item,image:item.image?`/media/${item.id.slice(6)}`:''};
  const button = LF.el('button','','lf-heart'); button.type='button';
  const sync = () => { const saved = LF.state.favorites[LF.profile()].some(x=>x.id===item.id); button.textContent=saved?'♥ Loved':'♡ Love'; button.setAttribute('aria-pressed',String(saved)); button.setAttribute('aria-label',`${saved?'Remove from':'Add to'} favorites: ${item.title}`); };
  button.onclick=async event => { event.preventDefault(); event.stopPropagation(); button.disabled=true; try { const saved=LF.state.favorites[LF.profile()].some(x=>x.id===item.id); await LF.save(`/api/favorites/${LF.profile()}`,saved?'DELETE':'PUT',item); LF.state.favorites[LF.profile()]=saved?LF.state.favorites[LF.profile()].filter(x=>x.id!==item.id):[...LF.state.favorites[LF.profile()],item]; document.dispatchEvent(new Event('lf-favorites')); LF.notify(saved?'Removed from favorites.':'Saved to favorites.'); } catch(error) { LF.notify(error.message); } finally {button.disabled=false;} };
  // A shared render updates connected buttons without accumulating event listeners.
  button._sync=sync; sync(); return button;
 };
 document.addEventListener('lf-favorites',()=> { document.querySelectorAll('.lf-heart').forEach(button=>button._sync?.()); renderFavorites(); });
 LF.openMedia = item => {
  const dialog=LF.el('dialog','','lf-media-viewer'); dialog.setAttribute('aria-label',item.title);
  const close=LF.el('button','×','lf-close'); close.setAttribute('aria-label','Close media'); close.onclick=()=>dialog.close();
  const media=LF.el(item.kind==='video'?'video':'img'); media.src=item.url;
  if(item.kind==='video') {media.controls=true;media.playsInline=true;media.autoplay=true;} else media.alt=item.title;
  dialog.append(close,media,LF.el('h2',item.title),LF.el('p',item.caption)); document.body.append(dialog);
  dialog.addEventListener('close',()=> {if(item.kind==='video') media.pause();dialog.remove();}); dialog.addEventListener('click',event=> {if(event.target===dialog)dialog.close();}); dialog.showModal();
 };
 LF.card = item => {
  const card=LF.el('article','','lf-card'); card.dataset.mediaId=item.id;
  const media=LF.el(item.kind==='video'?'video':'img'); media.src=item.url; media.dataset.managed='true';
  if(item.kind==='video') {media.controls=true;media.playsInline=true;media.preload='metadata';media.setAttribute('aria-label',item.title);} else {media.alt=item.title;media.loading='lazy';media.tabIndex=0;media.setAttribute('role','button');media.onclick=()=>LF.openMedia(item);media.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();LF.openMedia(item);}};}
  const edit=LF.el('button','Edit','lf-action'); edit.onclick=()=>LF.editMedia(item);
  card.append(media,LF.el('h2',item.title)); if(item.caption)card.append(LF.el('p',item.caption));
  card.append(LF.favorite({id:`media:${item.id}`,title:item.title,href:`gallery.html?media=${item.id}`,image:item.kind==='photo'?item.url:''}),edit); return card;
 };
 function renderFavorites() {
  const grid=document.getElementById('saved-favorites'); if(!grid || !LF.state)return; grid.replaceChildren();
  const items=LF.state.favorites[LF.profile()].filter(item=>!item.id.startsWith('media:') || !LF.media(item.id.slice(6))?.deleted);
  document.getElementById('favorites-empty').hidden=items.length>0;
  items.forEach(item=> { if(item.id.startsWith('media:')){const media=LF.media(item.id.slice(6));if(media)grid.append(LF.card(media));return;} const card=LF.el('article','','lf-card'),link=LF.el('a');link.href=item.href;if(item.image){const img=LF.el('img');img.src=item.image;img.alt=item.title;link.append(img);}link.append(LF.el('h2',item.title));card.append(link,LF.favorite(item));grid.append(card); });
 }
 LF.tile = item => {
  if(item.kind==='video') {const video=elVideo();return video;}
  function elVideo(){const video=LF.el('video');video.src=item.url;video.controls=true;video.playsInline=true;video.preload='metadata';video.dataset.managed='true';video.setAttribute('aria-label',item.title);return video;}
  const wrap=LF.el('div','','lf-photo');wrap.dataset.mediaId=item.id;const image=LF.el('img');image.src=item.url;image.alt=item.title;image.loading='lazy';image.dataset.managed='true';image.tabIndex=0;image.setAttribute('role','button');image.setAttribute('aria-label',`Open ${item.title}`);image.onclick=()=>LF.openMedia(item);image.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();LF.openMedia(item);}};
  const edit=LF.el('button','Edit','lf-inline-edit');edit.onclick=()=>LF.editMedia(item);wrap.append(image,LF.favorite({id:`media:${item.id}`,title:item.title,href:`gallery.html?media=${item.id}`,image:item.url}),edit);return wrap;
 };
 LF.page = () => { const page=location.pathname.split('/').pop(); const memory=new URLSearchParams(location.search).get('memory'); return page+(page==='memories.html'&&memory?'?memory='+memory:''); };
 const albumForPage = () => ({'gallery.html':'gallery','photos.html':'favorite','memory-details.html':'first-date','story-begins.html':'story-begins','best-part.html':'best-part','nagarkot-trip.html':'nagarkot','watch.html':'videos'})[location.pathname.split('/').pop()] || (location.pathname.endsWith('/memories.html') ? new URLSearchParams(location.search).get('memory') : null);
 function renderAlbum() {
  const collection=albumForPage(); if(!collection)return;
  let grid=document.querySelector('.gallery, .gallery-container, #memory-photos, #video-grid');
  if(!grid){grid=LF.el('section','','lf-grid');document.querySelector('main').append(grid);}
  grid.replaceChildren(); grid.classList.add('lf-album');
  LF.state.media.filter(item=>!item.deleted&&item.collections.includes(collection)).forEach(item=>{if(collection==='videos'){grid.append(LF.card(item));return;}const tile=LF.tile(item);if(collection==='favorite'){const cell=LF.el('div','','gallery-item');cell.append(tile);grid.append(cell);}else if(item.kind==='video'){const cell=LF.el('div','','lf-photo');const edit=LF.el('button','Edit','lf-inline-edit');edit.onclick=()=>LF.editMedia(item);cell.append(tile,edit);grid.append(cell);}else grid.append(tile);});
  if(!grid.children.length)grid.append(LF.el('p','No memories here yet. Add your first photo or video.'));
  if(!document.getElementById('lf-add-media')) {const button=LF.el('button','＋ Add photos or videos','lf-action');button.id='lf-add-media';button.onclick=()=>LF.addMedia(collection);grid.before(button);}
 }
 function syncMedia() {
  const byOriginal=new Map(LF.state.media.filter(x=>x.original).map(x=>[x.original,x]));
  document.querySelectorAll('img[src], img[data-original], video[src], video source[src]').forEach(node=> {
   if(node.dataset.managed || node.closest('.lf-media-viewer, .lf-editor, #media-library, #saved-favorites, .lf-album'))return;
   const original=node.dataset.original || node.getAttribute('src')?.replace(/^\//,''); const item=byOriginal.get(original); if(!item)return;
   node.dataset.original=original;
   const target=node.tagName==='SOURCE'?node.parentElement:node;
   if(item.deleted){target.hidden=true;if(target.parentElement.classList.contains('lf-photo'))target.parentElement.hidden=true;return;}target.hidden=false;if(target.parentElement.classList.contains('lf-photo'))target.parentElement.hidden=false;
   if(node.getAttribute('src')!==item.url){node.src=item.url;if(node.tagName==='SOURCE')node.parentElement.load();}
   if(node.tagName==='IMG'){node.alt=item.title;node.decoding='async';if(node.closest('.memory-card'))node.loading='lazy';}
   if(node.tagName==='IMG'&&!node.closest('a,.lf-photo')) {
    const wrap=LF.el('div','','lf-photo'); node.before(wrap);wrap.append(node,LF.favorite({id:`media:${item.id}`,title:item.title,href:`gallery.html?media=${item.id}`,image:item.url}));
    const edit=LF.el('button','Edit photo','lf-inline-edit');edit.onclick=()=>LF.editMedia(item);wrap.append(edit);
   }
  });
  const playMovie=LF.media('play-movie');
  if(window.setLoveFlixMovie && playMovie)window.setLoveFlixMovie(playMovie.deleted?null:playMovie.url);
 }
 function renderProfiles() {
  const current=LF.state.profiles.find(p=>p.id===LF.profile());
  document.querySelectorAll('.mini-profile').forEach(node=>{node.replaceChildren();node.setAttribute('aria-label',`${current.name}: switch profile`);if(current.picture){const img=LF.el('img');img.src=current.picture;img.alt=current.name;node.append(img);}else node.textContent=current.name[0];});
  document.querySelectorAll('.profile-card').forEach(card=> {const id=new URL(card.href).searchParams.get('profile');const p=LF.state.profiles.find(p=>p.id===id);if(!p)return;card.onclick=()=>localStorage.setItem('lf-active-profile',id); const avatar=card.querySelector('.avatar');avatar.replaceChildren();if(p.picture){const img=LF.el('img');img.src=p.picture;img.alt=p.name;avatar.append(img);}else avatar.textContent=p.name[0];card.querySelector(':scope > span').textContent=p.name;});
 }
 LF.render=()=>{renderAlbum();renderFavorites();renderProfiles();syncMedia();};
 document.addEventListener('visibilitychange',async()=>{if(!document.hidden&&LF.state&&!document.querySelector('dialog[open],.lf-editing')&&![...document.querySelectorAll('video')].some(v=>!v.paused)){try{await LF.refresh();LF.render();}catch(error){LF.notify(error.message);}}});
 LF.ready = new Promise(resolve=>document.readyState==='loading'?document.addEventListener('DOMContentLoaded',resolve,{once:true}):resolve()).then(async()=> {
  if(location.pathname.endsWith('login.html'))return;
  try {
   await LF.refresh(); LF.render();
   document.querySelectorAll('.memory-card').forEach(card=> {const href=card.getAttribute('href'),title=card.querySelector('strong')?.textContent||'Our memory';const wrap=LF.el('div','','lf-memory');card.before(wrap);wrap.append(card,LF.favorite({id:`memory:${href}`,title,href,image:card.querySelector('img')?.dataset.original||''}));});
   if(!['home.html','settings.html','profile.html','watch.html','favorites.html','login.html','index.html'].includes(location.pathname.split('/').pop())) {const heading=document.querySelector('main h1');if(heading)heading.after(LF.favorite({id:`page:${LF.page()}`,title:heading.textContent,href:LF.page(),image:''}));}
   const requested=new URLSearchParams(location.search).get('media');if(requested){const item=LF.media(requested);if(item&&!item.deleted)LF.openMedia(item);}
   document.dispatchEvent(new Event('lf-ready'));
  } catch(error) {LF.notify(error.message==='Failed to fetch'?'Start the LoveFlix server to load and save your memories.':error.message);}
 });
})();
