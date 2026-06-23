/**
 * validation.js
 * Client-side validation mirroring server-side WTForms rules.
 * • Bootstrap was-validated pattern
 * • Password toggle (eye icon)
 * • Submit spinner on valid form submission
 */

'use strict';

// ── Bootstrap was-validated ──────────────────────────────────────────────────
document.querySelectorAll('form.needs-validation').forEach(function (form) {
  form.addEventListener('submit', function (event) {
    // Custom cross-field validation before browser/Bootstrap validation
    const ok = runCustomValidation(form);
    if (!form.checkValidity() || !ok) {
      event.preventDefault();
      event.stopPropagation();
    } else {
      // Show spinner on the submit button
      const btn = form.querySelector('.pm-submit-btn');
      if (btn) {
        btn.querySelector('.pm-btn-text')?.classList.add('d-none');
        btn.querySelector('.pm-btn-spinner')?.classList.remove('d-none');
        btn.disabled = true;
      }
    }
    form.classList.add('was-validated');
  }, false);
});

/**
 * Custom cross-field validation rules not expressible via HTML5 attributes.
 * Returns true if all pass.
 */
function runCustomValidation(form) {
  let valid = true;

  // ── DOB: must be after 1900-01-01 and ≤ today ──────────────────────────
  const dobField = form.querySelector('#date_of_birth');
  if (dobField && dobField.value) {
    const dob = new Date(dobField.value);
    const minDate = new Date('1900-01-01');
    const today = new Date();
    today.setHours(23, 59, 59, 999); // allow today

    if (dob <= minDate) {
      setInvalid(dobField, 'Date of birth must be after 1900-01-01.');
      valid = false;
    } else if (dob > today) {
      setInvalid(dobField, 'Date of birth cannot be in the future.');
      valid = false;
    } else {
      setValid(dobField);
    }
  }

  // ── Password match ──────────────────────────────────────────────────────
  const pw  = form.querySelector('#password');
  const pw2 = form.querySelector('#confirm_password');
  if (pw && pw2 && pw.value && pw2.value) {
    if (pw.value !== pw2.value) {
      setInvalid(pw2, 'Passwords do not match.');
      valid = false;
    } else {
      setValid(pw2);
    }
  }

  // ── Numeric ranges ──────────────────────────────────────────────────────
  const ranges = [
    { id: 'glucose',      min: 20,  max: 800, unit: 'mg/dL' },
    { id: 'haemoglobin',  min: 2,   max: 25,  unit: 'g/dL'  },
    { id: 'cholesterol',  min: 50,  max: 500, unit: 'mg/dL' },
  ];
  ranges.forEach(function ({ id, min, max, unit }) {
    const field = form.querySelector('#' + id);
    if (field && field.value !== '') {
      const val = parseFloat(field.value);
      if (isNaN(val) || val < min || val > max) {
        setInvalid(field, `Value must be between ${min} and ${max} ${unit}.`);
        valid = false;
      }
    }
  });

  return valid;
}

function setInvalid(field, message) {
  field.classList.add('is-invalid');
  field.classList.remove('is-valid');
  // Update or create a JS-generated error message element
  let fb = field.parentElement.querySelector('.pm-js-feedback');
  if (!fb) {
    fb = document.createElement('div');
    fb.className = 'invalid-feedback pm-js-feedback';
    field.parentElement.appendChild(fb);
  }
  fb.textContent = message;
}

function setValid(field) {
  field.classList.remove('is-invalid');
  const fb = field.parentElement.querySelector('.pm-js-feedback');
  if (fb) fb.remove();
}

// ── Password Toggle ──────────────────────────────────────────────────────────
document.querySelectorAll('.pm-pw-toggle').forEach(function (btn) {
  btn.addEventListener('click', function () {
    const targetId = btn.getAttribute('data-target');
    const input = document.getElementById(targetId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    const icon = btn.querySelector('i');
    if (icon) {
      icon.className = isPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
    }
  });
});

// ── Auto-dismiss flash alerts after 6s ──────────────────────────────────────
setTimeout(function () {
  document.querySelectorAll('#flash-container .alert').forEach(function (el) {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
    bsAlert.close();
  });
}, 6000);
