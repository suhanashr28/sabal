const fallbackImage = 'images/placeholder.svg';

function replaceBrokenImage(image) {
    if (!image.dataset.fallbackApplied) {
        image.dataset.fallbackApplied = 'true';
        image.src = fallbackImage;
    }
}

document.querySelectorAll('img').forEach((image) => {
    image.addEventListener('error', () => replaceBrokenImage(image));
    if (image.hasAttribute('src') && image.complete && image.naturalWidth === 0) replaceBrokenImage(image);
});
