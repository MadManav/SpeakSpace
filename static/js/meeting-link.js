document.addEventListener('DOMContentLoaded', function() {
    // Get all meeting links
    const meetingLinks = document.querySelectorAll('[id^="meeting-link-"]');
    
    // Initialize each link
    meetingLinks.forEach(link => {
        const startTimeStr = link.getAttribute('data-start-time');
        const startTime = new Date(startTimeStr);
        const sessionId = link.getAttribute('data-session-id');
        const countdownElement = document.getElementById(`countdown-${sessionId}`);
        
        // Check if start time is in the future
        const currentTime = new Date();
        if (startTime > currentTime) {
            // Disable link
            link.setAttribute('disabled', 'disabled');
            link.style.pointerEvents = 'none';
            link.classList.add('opacity-50', 'cursor-not-allowed');
            
            // Start countdown
            updateCountdown(countdownElement, startTime);
            
            // Set timeout to enable link at start time
            const timeUntilStart = startTime - currentTime;
            setTimeout(() => {
                enableMeetingLink(link, countdownElement);
            }, timeUntilStart);
        } else {
            // Meeting time has already started
            enableMeetingLink(link, countdownElement);
        }
    });
    
    // Function to update countdown
    function updateCountdown(element, targetTime) {
        if (!element) return;
        
        const interval = setInterval(() => {
            const now = new Date();
            const diff = targetTime - now;
            
            if (diff <= 0) {
                clearInterval(interval);
                element.textContent = '(Meeting started)';
                return;
            }
            
            // Calculate hours, minutes, seconds
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            
            // Format countdown string
            let countdownStr = '(Starts in: ';
            if (hours > 0) countdownStr += `${hours}h `;
            countdownStr += `${minutes}m ${seconds}s)`;
            
            element.textContent = countdownStr;
        }, 1000);
    }
    
    // Function to enable meeting link
    function enableMeetingLink(link, countdownElement) {
        if (!link) return;
        
        // Enable link
        link.removeAttribute('disabled');
        link.style.pointerEvents = 'auto';
        link.classList.remove('opacity-50', 'cursor-not-allowed');
        
        // Update countdown text
        if (countdownElement) {
            countdownElement.textContent = '(Active now)';
        }
    }
});