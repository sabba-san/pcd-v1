document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        appendMessage('user', message);
        userInput.value = '';

        try {
            // Updated to Absolute URL for Port 5002
            const response = await fetch('http://127.0.0.1:5002/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();
            appendMessage('bot', data.response);
        } catch (error) {
            console.error("Connection Error:", error);
            appendMessage('bot', "Error: Could not connect to Jian Wei. Ensure Port 5002 is running.");
        }
    });

    function appendMessage(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}-message`;
        msgDiv.innerHTML = `
            <div class="message-content">${text}</div>
            <div class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
        `;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});

function runAssessment() {
    const type = document.getElementById('defectType').value;
    const within = document.getElementById('withinDLP').value;
    const result = document.getElementById('assessment-result');

    result.classList.remove('d-none');
    if (within === 'yes') {
        result.innerHTML = `✅ Your <strong>${type}</strong> is covered! You should file a notice.`;
        result.className = "mt-3 alert alert-success small";
    } else {
        result.innerHTML = `❌ Outside 24 months. You may need a lawyer for structural claims.`;
        result.className = "mt-3 alert alert-warning small";
    }
}