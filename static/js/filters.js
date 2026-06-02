/* ============================================
   VELEGRAD ESTATE — Listing Filters (server-side GET)
   --------------------------------------------
   Story 3.1: adaptirano sa client-side hide na GET form submit (arh §1.2).
   Filteri se primenjuju SERVERSKI — JS samo zadržava UX (price slider feedback,
   bedrooms chip → hidden input). Forma radi i bez JS-a (progressive enhancement).
   Bez fetch / XMLHttpRequest / XHR.

   Izmene u odnosu na 2.1 kopiju (Dev Agent Record):
     - Uklonjena client-side applyFilters()/resetFilters() hide logika
       (style.display nad .property-card) — primarni mehanizam je GET reload.
     - Selektori usklađeni sa novim name-ovima forme:
         [name="price-min"]  -> [name="price_min"]
         [name="price-max"]  -> [name="price_max"]
         [name="type"]       -> [name="property_type"] (čita se kroz formu, nema XHR)
     - Bedrooms chip klik upisuje vrednost u hidden <input name="bedrooms">
       ("5+" chip ima data-bedrooms="5") i submituje formu (GET).
   ============================================ */

(function () {
  'use strict';

  var filterBar = document.querySelector('.filter-bar');
  if (!filterBar) return;

  var form = filterBar.closest('form');
  var toggleBtn = filterBar.querySelector('.filter-bar__toggle');
  var optionalPanel = filterBar.querySelector('.filter-bar__optional');
  var bedroomsInput = filterBar.querySelector('input[type="hidden"][name="bedrooms"]');

  // Toggle optional filters (zadržano za eventualni opcioni panel)
  if (toggleBtn && optionalPanel) {
    toggleBtn.addEventListener('click', function () {
      var isOpen = optionalPanel.classList.toggle('is-visible');
      toggleBtn.textContent = isOpen ? 'Manje opcija' : 'Više opcija';
    });
  }

  // ── Bedroom chips → hidden input (GET submit) ──
  var chips = Array.from(filterBar.querySelectorAll('.chip[data-bedrooms]'));
  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var value = chip.getAttribute('data-bedrooms') || '';
      var alreadyActive = chip.classList.contains('is-active');

      chips.forEach(function (c) { c.classList.remove('is-active'); });

      if (alreadyActive) {
        // Re-klik na aktivni chip = deselekcija.
        if (bedroomsInput) bedroomsInput.value = '';
      } else {
        chip.classList.add('is-active');
        if (bedroomsInput) bedroomsInput.value = value;
      }
    });
  });

  // ── Dual range slider (vizuelni feedback) ──
  var sliderMin = filterBar.querySelector('.price-slider__input[name="price_min"]');
  var sliderMax = filterBar.querySelector('.price-slider__input[name="price_max"]');
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
})();
