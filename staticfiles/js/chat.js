document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-message-btn');
    const messagesContainer = document.getElementById('chat-messages');
    const roomId = document.getElementById('room-id').value;
    
    // Create WebSocket connection
    const chatSocket = new WebSocket(
        'ws://' + window.location.host + '/ws/chat/' + roomId + '/'
    );

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        const messageDiv = document.createElement('div');
        const isCurrentUser = data.username === currentUser;
        
        messageDiv.className = `message ${isCurrentUser ? 'sent' : 'received'} mb-4`;
        messageDiv.innerHTML = `
            <div class="flex items-start ${isCurrentUser ? 'justify-end' : ''}">
                <div class="flex items-start ${isCurrentUser ? 'bg-blue-600' : 'bg-gray-700'} rounded-lg px-4 py-2 max-w-[70%]">
                    <div>
                        <div class="font-semibold text-sm text-white">${data.username}</div>
                        <p class="text-white">${data.message}</p>
                        <span class="text-xs text-gray-300 mt-1">${new Date().toLocaleTimeString([], {hour: 'numeric', minute:'2-digit'})}</span>
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };

    chatSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
    };

    // Function to send message
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message === '') {
            return;
        }

        // Send message through WebSocket
        chatSocket.send(JSON.stringify({
            'message': message,
            'username': currentUser
        }));

        // Clear input
        messageInput.value = '';
    }

    // Send on button click
    if (sendButton) {
        sendButton.addEventListener('click', function() {
            sendMessage();
        });
    }

    // Send on Enter key press
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Auto-scroll to bottom on page load
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
});