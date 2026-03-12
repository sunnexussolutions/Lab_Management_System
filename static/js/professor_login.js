// Password visibility toggle
document.addEventListener('DOMContentLoaded', function() {
    const toggleButtons = document.querySelectorAll('.toggle-password');

    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.previousElementSibling; // Assuming input is right before the button
            const icon = this.querySelector('i');

            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            } else {
                input.type = 'password';
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            }
        });
    });
});

// Password match validation
document.addEventListener('DOMContentLoaded', function() {
    const password1 = document.getElementById('signupPassword');
    const password2 = document.getElementById('confirmPassword');
    const matchMessage = document.getElementById('passwordMatchMessage');

    if (password1 && password2 && matchMessage) {
        function checkPasswordMatch() {
            if (password2.value === '') {
                matchMessage.textContent = '';
                matchMessage.style.color = '';
                return;
            }

            if (password1.value === password2.value) {
                matchMessage.textContent = 'Passwords match';
                matchMessage.style.color = 'green';
            } else {
                matchMessage.textContent = 'Passwords do not match';
                matchMessage.style.color = 'red';
            }
        }

        password1.addEventListener('input', checkPasswordMatch);
        password2.addEventListener('input', checkPasswordMatch);
    }
});

// Update the selected divisions on the dropdown button
document.addEventListener('DOMContentLoaded', function() {
    const divisionCheckboxes = document.querySelectorAll('input[name="divisions"]');
    const divisionDropdownButton = document.getElementById('divisionDropdown');

    if (divisionDropdownButton && divisionCheckboxes.length > 0) {
        divisionCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const selectedDivisions = Array.from(divisionCheckboxes)
                    .filter(i => i.checked)
                    .map(i => i.value);
                
                if (selectedDivisions.length > 0) {
                    divisionDropdownButton.textContent = selectedDivisions.join(', ');
                } else {
                    divisionDropdownButton.textContent = 'Select divisions...';
                }
            });
        });
        
        // Prevent dropdown from closing when clicking a checkbox
        const dropdownMenu = divisionDropdownButton.nextElementSibling;
        if (dropdownMenu) {
            dropdownMenu.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        }
    }
});