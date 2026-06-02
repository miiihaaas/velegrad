/* ============================================
   VELEGRAD ESTATE — Listing Filters (client-side)
   ============================================ */

(function () {
  'use strict';

  var filterBar = document.querySelector('.filter-bar');
  if (!filterBar) return;

  var cards = Array.from(document.querySelectorAll('.property-card[data-filter]'));
  var toggleBtn = filterBar.querySelector('.filter-bar__toggle');
  var optionalPanel = filterBar.querySelector('.filter-bar__optional');
  var applyBtn = filterBar.querySelector('[data-action="apply"]');
  var resetBtn = filterBar.querySelector('[data-action="reset"]');
  var resultsEl = document.querySelector('.listing-results');
  var emptyEl = document.querySelector('.listing-empty');

  // Toggle optional filters
  if (toggleBtn && optionalPanel) {
    toggleBtn.addEventListener('click', function () {
      var isOpen = optionalPanel.classList.toggle('is-visible');
      toggleBtn.textContent = isOpen ? 'Manje opcija' : 'Više opcija';
    });
  }

  // Bedroom chips
  var chips = Array.from(filterBar.querySelectorAll('.chip[data-bedrooms]'));
  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      chip.classList.toggle('is-active');
    });
  });

  // ── Dual range slider ──
  var sliderMin = filterBar.querySelector('.price-slider__input[name="price-min"]');
  var sliderMax = filterBar.querySelector('.price-slider__input[name="price-max"]');
  var sliderFill = filterBar.querySelector('.price-slider__fill');
  var minValEl = filterBar.querySelector('.price-slider__min-val');
  var maxValEl = filterBar.querySelector('.price-slider__max-val');

  function formatPrice(val) {
    if (val >= 1000000) {
      return '€' + (val / 1000000).toFixed(val % 1000000 === 0 ? 0 : 1) + 'M';
    }
    return '€' + val.toLocaleString('sr-RS');
  }

  function updateSlider() {
    if (!sliderMin || !sliderMax) return;
    var min = parseInt(sliderMin.value);
    var max = parseInt(sliderMax.value);
    var total = parseInt(sliderMax.max);

    // Prevent crossing
    if (min > max) {
      sliderMin.value = max;
      min = max;
    }

    var leftPct = (min / total) * 100;
    var rightPct = (max / total) * 100;

    if (sliderFill) {
      sliderFill.style.left = leftPct + '%';
      sliderFill.style.width = (rightPct - leftPct) + '%';
    }
    if (minValEl) minValEl.textContent = formatPrice(min);
    if (maxValEl) maxValEl.textContent = formatPrice(max);
  }

  if (sliderMin) {
    sliderMin.addEventListener('input', updateSlider);
  }
  if (sliderMax) {
    sliderMax.addEventListener('input', updateSlider);
  }
  updateSlider();

  function getFilters() {
    var location = filterBar.querySelector('[name="location"]');
    var type = filterBar.querySelector('[name="type"]');
    var status = filterBar.querySelector('[name="status"]');

    var priceMin = sliderMin ? parseInt(sliderMin.value) || 0 : 0;
    var priceMax = sliderMax ? parseInt(sliderMax.value) || Infinity : Infinity;

    var activeChips = chips.filter(function (c) { return c.classList.contains('is-active'); });
    var bedrooms = activeChips.map(function (c) { return c.getAttribute('data-bedrooms'); });

    var checkboxes = Array.from(filterBar.querySelectorAll('.filter-checkbox input:checked'));
    var features = checkboxes.map(function (cb) { return cb.value; });

    return {
      location: location ? location.value : '',
      type: type ? type.value : '',
      status: status ? status.value : '',
      priceMin: priceMin,
      priceMax: priceMax,
      bedrooms: bedrooms,
      features: features
    };
  }

  function applyFilters() {
    var f = getFilters();
    var visibleCount = 0;

    cards.forEach(function (card) {
      var d = card.dataset;
      var show = true;

      if (f.location && d.location !== f.location) show = false;
      if (f.type && d.type !== f.type) show = false;
      if (f.status && d.status !== f.status) show = false;

      var price = parseInt(d.price) || 0;
      if (price > 0) {
        if (price < f.priceMin) show = false;
        if (price > f.priceMax) show = false;
      }

      if (f.bedrooms.length > 0) {
        var beds = d.bedrooms || '0';
        var match = f.bedrooms.some(function (b) {
          return b === '5+' ? parseInt(beds) >= 5 : beds === b;
        });
        if (!match) show = false;
      }

      if (f.features.length > 0) {
        var cardFeatures = (d.features || '').split(',');
        var allMatch = f.features.every(function (feat) {
          return cardFeatures.indexOf(feat) !== -1;
        });
        if (!allMatch) show = false;
      }

      card.style.display = show ? '' : 'none';
      if (show) visibleCount++;
    });

    if (resultsEl) {
      resultsEl.textContent = visibleCount + ' od ' + cards.length + ' nekretnina';
    }
    if (emptyEl) {
      emptyEl.style.display = visibleCount === 0 ? '' : 'none';
    }
  }

  function resetFilters() {
    var selects = filterBar.querySelectorAll('select');
    selects.forEach(function (s) { s.selectedIndex = 0; });

    var inputs = filterBar.querySelectorAll('input[type="text"]');
    inputs.forEach(function (i) { i.value = ''; });

    var checkboxes = filterBar.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(function (cb) { cb.checked = false; });

    chips.forEach(function (c) { c.classList.remove('is-active'); });

    // Reset slider
    if (sliderMin) sliderMin.value = sliderMin.min;
    if (sliderMax) sliderMax.value = sliderMax.max;
    updateSlider();

    cards.forEach(function (card) { card.style.display = ''; });

    if (resultsEl) {
      resultsEl.textContent = cards.length + ' od ' + cards.length + ' nekretnina';
    }
    if (emptyEl) {
      emptyEl.style.display = 'none';
    }
  }

  if (applyBtn) applyBtn.addEventListener('click', applyFilters);
  if (resetBtn) resetBtn.addEventListener('click', resetFilters);
})();
