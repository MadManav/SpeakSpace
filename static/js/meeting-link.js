document.addEventListener('DOMContentLoaded', function() {
    // Update all meeting links and countdowns
    function updateMeetingLinks() {
        const meetingLinks = document.querySelectorAll('[id^="meeting-link-"]');
        
        meetingLinks.forEach(link => {
            const sessionId = link.id.split('-').pop();
            const startTime = new Date(link.dataset.startTime);
            const now = new Date();
            const countdown = document.getElementById(`countdown-${sessionId}`);
            
            if (now < startTime) {
                // Meeting hasn't started yet
                link.classList.add('pointer-events-none', 'opacity-50');
                
                // Update countdown
                if (countdown) {
                    const diff = startTime - now;
                    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
                    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                    
                    let countdownText = '(Starts in: ';
                    if (days > 0) countdownText += `${days}d `;
                    if (hours > 0) countdownText += `${hours}h `;
                    countdownText += `${minutes}m)`;
                    
                    countdown.textContent = countdownText;
                }
            } else {
                // Meeting has started
                link.classList.remove('pointer-events-none', 'opacity-50');
                if (countdown) {
                    countdown.textContent = '(Meeting is live)';
                }
            }
        });
    }

    // Update every minute
    updateMeetingLinks();
    setInterval(updateMeetingLinks, 60000);
});