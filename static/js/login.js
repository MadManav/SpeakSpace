document.getElementById('loginForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        alert('Please fill in all fields');
        return;
    }
    
    localStorage.setItem('username', username);
    window.location.href = 'dashboard.html';
});

// Add ripple effect to button
document.querySelector('button').addEventListener('click', function(e) {
    const button = e.currentTarget;
    const ripple = document.createElement('div');
    const rect = button.getBoundingClientRect();
    
    ripple.className = 'ripple';
    ripple.style.left = `${e.clientX - rect.left}px`;
    ripple.style.top = `${e.clientY - rect.top}px`;
    
    button.appendChild(ripple);
    
    setTimeout(() => ripple.remove(), 600);
});