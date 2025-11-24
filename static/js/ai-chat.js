// AI Chat functionality
document.addEventListener('DOMContentLoaded', function () {
    const chatForm = document.getElementById('chatForm');
    const questionInput = document.getElementById('questionInput');
    const chatMessages = document.getElementById('chatMessages');
    const sendButton = document.getElementById('sendButton');

    if (chatForm) {
        chatForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const question = questionInput.value.trim();

            if (!question) {
                return;
            }

            // Add user message to chat
            addMessage('user', question);

            // Clear input
            questionInput.value = '';

            // Disable send button
            sendButton.disabled = true;
            sendButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Thinking...';

            try {
                const response = await fetch('/api/ask_ai', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ question })
                });

                const result = await response.json();

                if (result.success) {
                    addMessage('ai', result.answer, result.confidence);
                } else {
                    addMessage('error', result.error || 'Failed to get response');
                }
            } catch (error) {
                console.error('Error:', error);
                addMessage('error', 'Network error occurred. Please try again.');
            } finally {
                // Re-enable send button
                sendButton.disabled = false;
                sendButton.innerHTML = '<i class="material-icons align-middle">send</i> Send';
                questionInput.focus();
            }
        });
    }
});

function addMessage(type, message, confidence = null) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'mb-3';

    if (type === 'user') {
        messageDiv.innerHTML = `
            <div class="d-flex justify-content-end">
                <div class="bg-primary text-white p-3 rounded-3" style="max-width: 70%;">
                    <strong>You:</strong>
                    <p class="mb-0 mt-1">${escapeHtml(message)}</p>
                </div>
            </div>
        `;
    } else if (type === 'ai') {
        const confidenceBadge = confidence ?
            `<span class="badge ${confidence >= 0.7 ? 'bg-success' : (confidence >= 0.5 ? 'bg-warning' : 'bg-danger')} ms-2">
                ${(confidence * 100).toFixed(0)}% confidence
            </span>` : '';

        messageDiv.innerHTML = `
            <div class="d-flex justify-content-start">
                <div class="bg-light p-3 rounded-3 border" style="max-width: 70%;">
                    <strong>
                        <i class="material-icons align-middle" style="font-size: 18px;">smart_toy</i>
                        AI Assistant ${confidenceBadge}
                    </strong>
                    <p class="mb-0 mt-1">${escapeHtml(message)}</p>
                </div>
            </div>
        `;
    } else if (type === 'error') {
        messageDiv.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="material-icons align-middle">error</i>
                ${escapeHtml(message)}
            </div>
        `;
    }

    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
