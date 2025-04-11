document.addEventListener('DOMContentLoaded', function() {
    // Clear autofill trap fields
    document.querySelector('input[name="fakeusernameremembered"]').value = '';
    document.querySelector('input[name="fakepasswordremembered"]').value = '';

    // Form validation
    const form = document.querySelector('form');
    form.addEventListener('submit', function(e) {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;

        if (!username || !password) {
            e.preventDefault();
            alert('Please fill in all fields');
        }
    });

    // Auto-hide messages after 5 seconds
    const messages = document.querySelectorAll('.messages div');
    messages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });
});