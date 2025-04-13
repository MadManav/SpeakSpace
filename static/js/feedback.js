document.addEventListener('DOMContentLoaded', function() {
    // References to DOM elements
    const feedbackModal = document.getElementById('feedback-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const submitFeedbackBtn = document.getElementById('submit-feedback');
    const ratingSlider = document.getElementById('rating-slider');
    const ratingValue = document.getElementById('rating-value');
    const feedbackComments = document.getElementById('feedback-comments');
    const sessionIdInput = document.getElementById('session-id-input');
    const modalParticipant = document.getElementById('modal-participant');
    const modalTopic = document.getElementById('modal-topic');
    
    // Track sessions that need feedback
    const completedSessions = new Set();
    
    // Update the rating value display when the slider changes
    ratingSlider.addEventListener('input', function() {
        ratingValue.textContent = this.value;
    });
    
    // Close modal when close button is clicked
    closeModalBtn.addEventListener('click', function() {
        feedbackModal.classList.add('hidden');
    });
    
    // Submit feedback when the submit button is clicked
    submitFeedbackBtn.addEventListener('click', submitFeedback);
    
    // Initialize all session timers
    initializeSessionTimers();
    
    // Initialize any existing review buttons
    document.querySelectorAll('.review-button').forEach(button => {
        button.addEventListener('click', openFeedbackModal);
    });
    
    // Function to initialize session timers
    function initializeSessionTimers() {
        const meetingLinks = document.querySelectorAll('[id^="meeting-link-"]');
        
        meetingLinks.forEach(link => {
            const sessionId = link.dataset.sessionId;
            const startTime = new Date(link.dataset.startTime);
            const duration = parseInt(link.dataset.duration) || 1; // Default to 60 minutes
            const endTime = new Date(startTime.getTime() + duration * 60000);
            
            // Check if meeting already ended
            const now = new Date();
            if (now > endTime) {
                showReviewButton(sessionId);
            } else {
                // Set timer for the end of the meeting
                const timeUntilEnd = endTime - now;
                if (timeUntilEnd > 0) {
                    setTimeout(() => {
                        showReviewButton(sessionId);
                    }, timeUntilEnd);
                }
            }
        });
    }
    
    // Function to show the review button
    function showReviewButton(sessionId) {
        const reviewBtn = document.getElementById(`review-btn-${sessionId}`);
        const sessionCard = document.getElementById(`session-card-${sessionId}`);
        const statusBadge = sessionCard.querySelector('.session-status');
        
        // Update status badge
        if (statusBadge) {
            statusBadge.textContent = 'Completed';
            statusBadge.classList.remove('bg-blue-200', 'dark:bg-blue-800', 'text-blue-800', 'dark:text-blue-200');
            statusBadge.classList.add('bg-green-200', 'dark:bg-green-800', 'text-green-800', 'dark:text-green-200');
        }
        
        // Show review button if it exists
        if (reviewBtn) {
            reviewBtn.classList.remove('hidden');
            reviewBtn.addEventListener('click', openFeedbackModal);
            
            // Add to set of sessions that need feedback
            completedSessions.add(sessionId);
        }
    }
    
    // Function to open the feedback modal
    function openFeedbackModal(event) {
        const button = event.currentTarget;
        const sessionId = button.dataset.sessionId;
        const participant = button.dataset.participant;
        const topic = button.dataset.topic;
        
        // Populate modal
        sessionIdInput.value = sessionId;
        modalParticipant.textContent = participant;
        modalTopic.textContent = topic;
        
        // Reset form
        ratingSlider.value = 7;
        ratingValue.textContent = '7';
        feedbackComments.value = '';
        
        // Show modal
        feedbackModal.classList.remove('hidden');
    }
    
    // Function to submit feedback
    function submitFeedback() {
        const sessionId = sessionIdInput.value;
        const rating = ratingSlider.value;
        const comments = feedbackComments.value;
        
        // Validate inputs
        if (!rating || !sessionId) {
            alert('Please provide a rating.');
            return;
        }
        
        // Send feedback to server
        fetch('/submit-feedback/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                session_id: sessionId,
                rating: rating,
                comments: comments
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Hide review button and show success message
                const reviewBtn = document.getElementById(`review-btn-${sessionId}`);
                const feedbackStatus = document.getElementById(`feedback-status-${sessionId}`);
                
                if (reviewBtn) reviewBtn.classList.add('hidden');
                if (feedbackStatus) feedbackStatus.classList.remove('hidden');
                
                // Close modal
                feedbackModal.classList.add('hidden');
                
                // Remove from set of sessions that need feedback
                completedSessions.delete(sessionId);
            } else {
                alert('Error submitting feedback: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while submitting feedback.');
        });
    }
    
    // Helper function to get CSRF token
    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
});