// Password visibility toggle
document.querySelectorAll('.toggle-password').forEach(toggle => {
  toggle.addEventListener('click', function () {
    const input = this.previousElementSibling;
    if (input && input.tagName === 'INPUT') {
      const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
      input.setAttribute('type', type);
      const icon = this.querySelector('i');
      icon.classList.toggle('bi-eye');
      icon.classList.toggle('bi-eye-slash');
    }
  });
});

// Password match validation (Registration only)
const signupForm = document.getElementById('signupForm');
const passwordInput = document.getElementById('signupPassword');
const confirmInput = document.getElementById('confirmPassword');
const matchMessage = document.getElementById('passwordMatchMessage');

function checkPasswordMatch() {
  const pass = passwordInput.value;
  const confirm = confirmInput.value;

  if (confirm === '') {
    matchMessage.textContent = '';
    confirmInput.classList.remove('is-valid', 'is-invalid');
    return;
  }

  if (pass === confirm && pass !== '') {
    matchMessage.textContent = 'Passwords match ✓';
    matchMessage.style.color = '#198754';
    confirmInput.classList.remove('is-invalid');
    confirmInput.classList.add('is-valid');
  } else {
    matchMessage.textContent = 'Passwords do not match ✗';
    matchMessage.style.color = '#dc3545';
    confirmInput.classList.remove('is-valid');
    confirmInput.classList.add('is-invalid');
  }
}

passwordInput?.addEventListener('input', checkPasswordMatch);
confirmInput?.addEventListener('input', checkPasswordMatch);

// Prevent signup submit if passwords don't match
signupForm?.addEventListener('submit', function (e) {
  if (passwordInput.value !== confirmInput.value) {
    e.preventDefault();
    matchMessage.textContent = 'Passwords do not match ✗';
    matchMessage.style.color = '#dc3545';
    confirmInput.classList.add('is-invalid');
    confirmInput.focus();
  }
});
// Dependent Dropdowns: Division → Lab → Professor
// Lab Data Mapping
// const labData = {
//   "J1": [
//     { id: 1, text: "Artificial Intelligence Lab (NYCM412)", prof: "Mrs. Shardha Bhamre / Sanjeev Shukla" },
//     { id: 2, text: "Database Management System Lab (NYCM411)", prof: "Dr. Sudhir Kumar Meshala" }
//   ],
//   "J2": [
//     { id: 1, text: "Artificial Intelligence Lab (NYCM412)", prof: "Mrs. Shardha Bhamre / Sanjeev Shukla" },
//     { id: 2, text: "Database Management System Lab (NYCM411)", prof: "Dr. Sudhir Kumar Meshala" }
//   ],
//   "J3": [],
//   "K2": [],
//   "L1": []
// };

function setupDropdown(divisionId, labId, professorId) {
  const divisionSelect = document.getElementById(divisionId);
  const labSelect = document.getElementById(labId);
  const professorInput = document.getElementById(professorId);

  if (!divisionSelect || !labSelect || !professorInput) return;

  divisionSelect.addEventListener('change', function () {
    const div = this.value;
    labSelect.innerHTML = '<option value="">Choose lab...</option>';
    labSelect.disabled = false;
    professorInput.value = '';

    if (div && labData[div]) {
      labData[div].forEach(lab => {
        const option = document.createElement('option');
        option.value = lab.id;
        option.textContent = lab.text;
        option.dataset.prof = lab.prof;
        labSelect.appendChild(option);
      });
    } else {
      labSelect.innerHTML = '<option value="">No labs available</option>';
      labSelect.disabled = true;
    }
  });

  labSelect.addEventListener('change', function () {
    const selected = this.options[this.selectedIndex];
    professorInput.value = selected.dataset.prof || '';
  });
}

// Call for both forms
setupDropdown("signinDivision", "signinLab", "signinProfessor");
setupDropdown("registerDivision", "registerLab", "registerProfessor");