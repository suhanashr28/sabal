const lightbox = document.getElementById('lightbox');
const lightboxImage = document.getElementById('lightbox-img');

document.querySelectorAll('.gallery-container img').forEach((image) => {
    image.addEventListener('click', () => {
        lightboxImage.src = image.src;
        lightbox.classList.add('show');
    });
});

lightbox?.addEventListener('click', () => lightbox.classList.remove('show'));
