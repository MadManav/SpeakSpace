document.addEventListener('DOMContentLoaded', function() {
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const messagesContainer = document.getElementById('chat-messages');

    messageForm.addEventListener('submit', function(e) {
        e.preventDefault(); // Prevent form from submitting normally

        const formData = new FormData(this);
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        fetch('/send-message/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Create new message element
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message sent mb-4';
                messageDiv.innerHTML = `
                    <div class="flex items-start justify-end">
                        <div class="flex items-start bg-blue-600 rounded-lg px-4 py-2 max-w-[70%]">
                            <div>
                                <div class="font-semibold text-sm text-white">${data.message.user}</div>
                                <p class="text-white">${data.message.content}</p>
                                <span class="text-xs text-gray-300 mt-1">${data.message.timestamp}</span>
                            </div>
                        </div>
                    </div>
                `;
                
                // Add message to chat
                messagesContainer.appendChild(messageDiv);
                
                // Clear input
                messageInput.value = '';
                
                // Scroll to bottom
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        })
        .catch(error => console.error('Error:', error));
    });
});