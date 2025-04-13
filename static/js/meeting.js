function updateMeetingLinks() {
    const meetingLinks = document.querySelectorAll('[data-start-time]');
    
    meetingLinks.forEach(link => {
        const linkId = link.id.split('-').pop(); // Extract session ID from the element ID
        const now = new Date().getTime();
        const meetingTime = new Date(link.dataset.startTime).getTime();
        const timeLeft = meetingTime - now;
        
        const countdown = document.getElementById(`countdown-${linkId}`);
        
        if (!countdown) return; // Skip if countdown element doesn't exist
        
        if (timeLeft > 0) {
            // Meeting hasn't started yet
            link.setAttribute('disabled', true);
            link.classList.add('opacity-50', 'cursor-not-allowed');
            link.classList.remove('hover:underline');
            
            // Format countdown
            const hours = Math.floor(timeLeft / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
            countdown.textContent = `(Starts in: ${hours}h ${minutes}m ${seconds}s)`;
        } else {
            // Meeting can be joined
            link.removeAttribute('disabled');
            link.classList.remove('opacity-50', 'cursor-not-allowed');
            link.classList.add('hover:underline');
            countdown.textContent = ''; // Clear the countdown
        }
    });
}

// Update every second
setInterval(updateMeetingLinks, 1000);

// Initialize on page load
document.addEventListener('DOMContentLoaded', updateMeetingLinks);

// Prevent clicking on disabled links
document.addEventListener('click', (e) => {
    if (e.target.hasAttribute('data-start-time') && e.target.hasAttribute('disabled')) {
        e.preventDefault();
        alert('This meeting has not started yet. Please wait for the scheduled time.');
    }
});