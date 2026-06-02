/* ============================================
   VELEGRAD ESTATE — Gallery Lightbox
   ============================================ */

(function () {
  'use strict';

  var lightbox = document.querySelector('.lightbox');
  if (!lightbox) return;

  var lightboxImg = lightbox.querySelector('.lightbox__img');
  var prevBtn = lightbox.querySelector('.lightbox__prev');
  var nextBtn = lightbox.querySelector('.lightbox__next');
  var closeBtn = lightbox.querySelector('.lightbox__close');
  var counter = lightbox.querySelector('.lightbox__counter');

  var thumbnails = Array.from(document.querySelectorAll('.thumbnail-strip__item'));
  var heroImg = document.querySelector('.detail-hero img');

  var images = [];
  var currentIndex = 0;

  // Collect all image sources
  if (heroImg) {
    images.push(heroImg.getAttribute('src'));
  }
  thumbnails.forEach(function (thumb) {
    var img = thumb.querySelector('img');
    if (img) {
      var src = img.getAttribute('data-full') || img.getAttribute('src');
      if (images.indexOf(src) === -1) {
        images.push(src);
      }
    }
  });

  function openLightbox(index) {
    currentIndex = index;
    updateLightbox();
    lightbox.classList.add('is-open');
    document.body.classList.add('scroll-locked');
  }

  function closeLightbox() {
    lightbox.classList.remove('is-open');
    document.body.classList.remove('scroll-locked');
  }

  function updateLightbox() {
    if (images[currentIndex]) {
      lightboxImg.setAttribute('src', images[currentIndex]);
      lightboxImg.setAttribute('alt', 'Fotografija ' + (currentIndex + 1) + ' od ' + images.length);
    }
    if (counter) {
      counter.textContent = (currentIndex + 1) + ' / ' + images.length;
    }
    // Update thumbnail active state
    thumbnails.forEach(function (thumb, i) {
      // offset by 1 because hero is index 0
      thumb.classList.toggle('is-active', i === currentIndex - 1 || (currentIndex === 0 && i === 0));
    });
  }

  function nextImage() {
    currentIndex = (currentIndex + 1) % images.length;
    updateLightbox();
  }

  function prevImage() {
    currentIndex = (currentIndex - 1 + images.length) % images.length;
    updateLightbox();
  }

  // Event listeners
  if (heroImg) {
    heroImg.addEventListener('click', function () { openLightbox(0); });
  }

  thumbnails.forEach(function (thumb, i) {
    thumb.addEventListener('click', function () {
      openLightbox(i + 1);
    });
  });

  if (closeBtn) closeBtn.addEventListener('click', closeLightbox);
  if (nextBtn) nextBtn.addEventListener('click', nextImage);
  if (prevBtn) prevBtn.addEventListener('click', prevImage);

  // Close on backdrop click
  lightbox.addEventListener('click', function (e) {
    if (e.target === lightbox) closeLightbox();
  });

  // Keyboard
  document.addEventListener('keydown', function (e) {
    if (!lightbox.classList.contains('is-open')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'ArrowLeft') prevImage();
  });

  // Touch swipe (Story 3.2, FR10/NFR-2): swipe left -> next, right -> prev.
  // A minimal touchstart/touchend delta on the lightbox; threshold avoids taps.
  var touchStartX = null;
  var SWIPE_THRESHOLD = 40;
  lightbox.addEventListener('touchstart', function (e) {
    if (e.changedTouches && e.changedTouches.length) {
      touchStartX = e.changedTouches[0].clientX;
    }
  }, { passive: true });
  lightbox.addEventListener('touchend', function (e) {
    if (touchStartX === null) return;
    var endX = (e.changedTouches && e.changedTouches.length)
      ? e.changedTouches[0].clientX
      : touchStartX;
    var delta = endX - touchStartX;
    if (delta < -SWIPE_THRESHOLD) {
      nextImage();
    } else if (delta > SWIPE_THRESHOLD) {
      prevImage();
    }
    touchStartX = null;
  }, { passive: true });
})();
