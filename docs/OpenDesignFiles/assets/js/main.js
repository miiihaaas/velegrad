/* ============================================
   VELEGRAD ESTATE — Main JS
   ============================================ */

(function () {
  'use strict';

  /* ── Sticky Header ── */

  var header = document.querySelector('.site-header');

  function updateHeader() {
    if (!header) return;
    if (window.scrollY > 40) {
      header.classList.add('is-scrolled');
    } else {
      // Don't remove is-scrolled if header starts with it (inner pages)
      if (!header.dataset.alwaysScrolled) {
        header.classList.remove('is-scrolled');
      }
    }
  }

  if (header) {
    // If header already has is-scrolled class on load, keep it
    if (header.classList.contains('is-scrolled')) {
      header.dataset.alwaysScrolled = 'true';
    }
    window.addEventListener('scroll', updateHeader, { passive: true });
    updateHeader();
  }

  /* ── Mobile Menu ── */

  var menuToggle = document.querySelector('.mobile-menu-toggle');
  var mobileMenu = document.querySelector('.mobile-menu');

  if (menuToggle && mobileMenu) {
    menuToggle.addEventListener('click', function () {
      var isOpen = menuToggle.classList.toggle('is-open');
      mobileMenu.classList.toggle('is-open');
      menuToggle.setAttribute('aria-expanded', String(isOpen));

      if (isOpen) {
        document.body.classList.add('scroll-locked');
      } else {
        document.body.classList.remove('scroll-locked');
      }
    });

    // Close menu when a link is clicked
    var menuLinks = mobileMenu.querySelectorAll('a');
    menuLinks.forEach(function (link) {
      link.addEventListener('click', function () {
        menuToggle.classList.remove('is-open');
        mobileMenu.classList.remove('is-open');
        menuToggle.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('scroll-locked');
      });
    });
  }

  /* ── Language Switcher (visual only) ── */

  var langButtons = document.querySelectorAll('.lang-switcher__btn');

  langButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      // Find sibling buttons in same switcher
      var switcher = btn.closest('.lang-switcher');
      if (!switcher) return;
      var siblings = switcher.querySelectorAll('.lang-switcher__btn');
      siblings.forEach(function (s) { s.classList.remove('is-active'); });
      btn.classList.add('is-active');

      // Also update other switchers on the page
      var lang = btn.getAttribute('data-lang');
      document.querySelectorAll('.lang-switcher__btn[data-lang="' + lang + '"]').forEach(function (b) {
        var parentSwitcher = b.closest('.lang-switcher');
        if (parentSwitcher) {
          parentSwitcher.querySelectorAll('.lang-switcher__btn').forEach(function (s) {
            s.classList.remove('is-active');
          });
        }
        b.classList.add('is-active');
      });
    });
  });

  /* ── Scroll Fade-In ── */

  var fadeElements = document.querySelectorAll('.fade-in-section');

  if (fadeElements.length > 0 && 'IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -40px 0px'
    });

    fadeElements.forEach(function (el) {
      observer.observe(el);
    });
  } else {
    // Fallback: show everything
    fadeElements.forEach(function (el) {
      el.classList.add('is-visible');
    });
  }

})();
