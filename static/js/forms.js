/* ============================================
   VELEGRAD ESTATE — Form Validation (client-side)
   ============================================ */

(function () {
  'use strict';

  var forms = document.querySelectorAll('[data-validate]');

  var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  var phoneRegex = /^[\+]?[\d\s\-\(\)]{7,20}$/;

  function validateField(input) {
    var value = input.value.trim();
    var type = input.type;
    var isRequired = input.hasAttribute('required');

    // Remove previous error
    var existingError = input.parentNode.querySelector('.form-error');
    if (existingError) existingError.remove();
    input.style.borderColor = '';

    if (isRequired && !value) {
      showError(input, 'Ovo polje je obavezno.');
      return false;
    }

    if (type === 'email' && value && !emailRegex.test(value)) {
      showError(input, 'Unesite ispravnu email adresu.');
      return false;
    }

    if (type === 'tel' && value && !phoneRegex.test(value)) {
      showError(input, 'Unesite ispravan broj telefona.');
      return false;
    }

    // Select validation
    if (input.tagName === 'SELECT' && isRequired && !value) {
      showError(input, 'Izaberite opciju.');
      return false;
    }

    return true;
  }

  function showError(input, message) {
    input.style.borderColor = 'var(--color-error)';
    var errorEl = document.createElement('span');
    errorEl.className = 'form-error';
    errorEl.textContent = message;
    input.parentNode.appendChild(errorEl);
  }

  forms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var inputs = form.querySelectorAll('input, select, textarea');
      var isValid = true;

      inputs.forEach(function (input) {
        if (!validateField(input)) {
          isValid = false;
        }
      });

      if (isValid) {
        // Show success message
        var successEl = form.querySelector('.form-success');
        if (successEl) {
          successEl.classList.add('is-visible');
        }

        // Reset form
        form.reset();

        // Hide success after 5 seconds
        setTimeout(function () {
          if (successEl) successEl.classList.remove('is-visible');
        }, 5000);
      }
    });

    // Real-time validation on blur
    var inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(function (input) {
      input.addEventListener('blur', function () {
        validateField(input);
      });
    });
  });
})();
