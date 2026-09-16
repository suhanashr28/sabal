(() => {
  const viewer = document.createElement('div');
  viewer.className = 'photo-lightbox';
  viewer.setAttribute('role', 'dialog');
  viewer.setAttribute('aria-label', 'Expanded photo');
  viewer.innerHTML = '<button type="button" aria-label="Close photo">×</button><img alt="">';
  const image = viewer.querySelector('img');
  const close = () => { viewer.classList.remove('open'); document.body.style.overflow = ''; };
  document.addEventListener('DOMContentLoaded', () => {
    document.body.append(viewer);
    document.querySelectorAll('img').forEach((photo) => {
      if (photo.closest('.photo-lightbox, .photo-viewer, .profile-card') || photo.id === 'profile-preview') return;
      if (photo.closest('.gallery') && document.querySelector('.photo-viewer')) return;
      photo.classList.add('click-to-expand');
      photo.tabIndex = 0;
      photo.setAttribute('role', 'button');
      photo.setAttribute('aria-label', `Expand photo: ${photo.alt || 'Our memory'}`);
      photo.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); photo.click(); } });
      photo.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        image.src = photo.currentSrc || photo.src;
        image.alt = photo.alt || 'Expanded photo';
        viewer.classList.add('open');
        document.body.style.overflow = 'hidden';
      });
    });
    document.querySelectorAll('.home-page .memory-card').forEach(card => {
      card.addEventListener('click', event => {event.preventDefault();card.querySelector('img')?.click();});
    });
  });
  viewer.addEventListener('click', (event) => { if (event.target === viewer || event.target.tagName === 'BUTTON') close(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') close(); });
  const style = document.createElement('style');
  style.textContent = '.click-to-expand{cursor:zoom-in}.photo-lightbox{display:none;position:fixed;inset:0;z-index:99999;place-items:center;padding:72px 9vw;background:rgba(0,0,0,.91)}.photo-lightbox.open{display:grid}.photo-lightbox img{max-width:82vw;max-height:78vh;width:auto;height:auto;object-fit:contain;cursor:zoom-out}.photo-lightbox button{position:absolute;top:18px;right:22px;border:0;background:transparent;color:#fff;font:42px/1 Arial;cursor:pointer;z-index:1}@media(max-width:600px){.photo-lightbox{padding:60px 18px}.photo-lightbox img{max-width:94vw;max-height:78vh}}';
  document.head.append(style);
})();
