document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');

    // 1. Handle Message Sending
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        // Add User Message to UI
        appendMessage('user', message);
        userInput.value = '';
        scrollToBottom();

        // Show "Typing..." indicator (Optional)
        const loadingId = appendLoadingMessage();

        try {
            // Call API
            const response = await fetch('/module4/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });
            
            const data = await response.json();
            
            // Remove loading and add Bot Message
            removeMessage(loadingId);
            
            if (data.error) {
                appendMessage('bot', "Error: " + data.error);
            } else {
                appendMessage('bot', data.reply);
            }

        } catch (error) {
            removeMessage(loadingId);
            appendMessage('bot', "Sorry, I'm having trouble connecting to the server.");
        }
        
        scrollToBottom();
    });

    // Helper: Append Message
    function appendMessage(sender, text) {
        const div = document.createElement('div');
        div.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');
        
        const content = `
            <div class="message-content">${text}</div>
            <div class="message-time">Just now</div>
        `;
        div.innerHTML = content;
        chatBox.appendChild(div);
    }

    // Helper: Loading Animation
    function appendLoadingMessage() {
        const id = 'loading-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.classList.add('message', 'bot-message');
        div.innerHTML = `<div class="message-content text-muted"><em>Jian Wei is typing...</em></div>`;
        chatBox.appendChild(div);
        return id;
    }

    function removeMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});

// Simple Logic for the Assessment Tool (Right Sidebar)
function runAssessment() {
    const isWithinDLP = document.getElementById('withinDLP').value;
    const resultDiv = document.getElementById('assessment-result');
    
    resultDiv.classList.remove('d-none', 'alert-success', 'alert-danger');
    
    if (isWithinDLP === 'yes') {
        resultDiv.classList.add('alert-success');
        resultDiv.innerHTML = "<strong>Eligible:</strong> The developer is likely liable to fix this at no cost.";
    } else {
        resultDiv.classList.add('alert-danger');
        resultDiv.innerHTML = "<strong>Not Eligible:</strong> The DLP has expired. You may need to bear the repair cost.";
    }
}