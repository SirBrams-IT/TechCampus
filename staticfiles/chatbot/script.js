// static/chatbot/script.js
function sendMessage() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to UI
    addMessage('user', message);
    input.value = '';
    
    // Show loading indicator
    const loadingId = showLoading();
    
    // Send to backend
    fetch('/chatbot/chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        // Remove loading indicator
        removeLoading(loadingId);
        
        if (data.error) {
            addMessage('bot', `Error: ${data.error}`);
        } else {
            addMessage('bot', data.response);
        }
    })
    .catch(error => {
        removeLoading(loadingId);
        addMessage('bot', 'Sorry, there was an error connecting to the server.');
    });
}

function addMessage(sender, text) {
    const container = document.getElementById('messagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.innerHTML = formatMessage(text);
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function formatMessage(text) {
    // Simple formatting for code blocks
    return text.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
               .replace(/`([^`]+)`/g, '<code>$1</code>')
               .replace(/\n/g, '<br>');
}

function showLoading() {
    const container = document.getElementById('messagesContainer');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot-message';
    loadingDiv.id = 'loading-' + Date.now();
    loadingDiv.innerHTML = '<em>Thinking...</em>';
    container.appendChild(loadingDiv);
    container.scrollTop = container.scrollHeight;
    return loadingDiv.id;
}

function removeLoading(loadingId) {
    const loadingElement = document.getElementById(loadingId);
    if (loadingElement) {
        loadingElement.remove();
    }
}

function fillSuggestion(text) {
    document.getElementById('userInput').value = text;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Handle Enter key
document.getElementById('userInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});