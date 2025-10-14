// DOM refs
const messagesContainer = document.getElementById('messagesContainer');
const chatSessionsEl = document.getElementById('chatSessions');
const userInput = document.getElementById('userInput');
const fileInput = document.getElementById('fileInput');
const audioBtn = document.getElementById('audioBtn');
const sendBtn = document.getElementById('sendBtn');
const btnNewChat = document.getElementById('btnNewChat');

let activeUuid = null;
let activeConversationId = null;

// load user's conversations
function loadConversations() {
    fetch('/chatbot/conversations/')
    .then(r => r.json())
    .then(data => {
        chatSessionsEl.innerHTML = '';
        const list = data.conversations || [];
        if (!list.length) {
            chatSessionsEl.innerHTML = '<div class="session-item">No conversations yet. Click New Chat.</div>';
            return;
        }
        list.forEach(s => {
            const div = document.createElement('div');
            div.className = 'session-item';
            div.dataset.uuid = s.uuid;
            div.dataset.convId = s.id;
            div.innerHTML = `<strong>${escapeHtml(s.title)}</strong><div style="font-size:12px;color:#9fb9c3;margin-top:6px">${escapeHtml(s.snippet)}</div>`;
            div.addEventListener('click', () => openConversation(s.uuid));
            chatSessionsEl.appendChild(div);
        });
    })
    .catch(() => chatSessionsEl.innerHTML = '<div class="session-item">Could not load conversations.</div>');
}

// open a conversation (load messages)
function openConversation(uuid) {
    activeUuid = uuid;
    messagesContainer.innerHTML = '<div class="bot-message message"><div class="text">Loading…</div></div>';
    fetch(`/chatbot/messages/?uuid=${encodeURIComponent(uuid)}`)
    .then(r => r.json())
    .then(data => {
        messagesContainer.innerHTML = '';
        if (data.error) { addSystem(data.error); return; }
        data.messages.forEach(m => appendMessage(m.sender, m.text, m.file));
        if (data.conversation) activeConversationId = data.conversation.id;
    })
    .catch(() => addSystem('Failed to load conversation.'));
}

// create new conversation
btnNewChat && btnNewChat.addEventListener('click', () => {
    fetch('/chatbot/create/', {method: 'POST', headers: {'X-CSRFToken': getCookie('csrftoken')}})
    .then(r => r.json())
    .then(data => {
        if (data.session_uuid) {
            openConversation(data.session_uuid);
            loadConversations();
        } else addSystem('Could not create conversation.');
    })
    .catch(() => addSystem('Could not create conversation.'));
});

// send message with optional file
sendBtn && sendBtn.addEventListener('click', sendMessage);
userInput && userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

function sendMessage() {
    const text = userInput.value.trim();
    const file = fileInput.files[0];

    if (!text && !file) return;

    if (text) appendMessage('user', text);

    const form = new FormData();
    if (text) form.append('message', text);
    if (activeUuid) form.append('session_uuid', activeUuid);
    if (file) form.append('file', file);

    const loading = showLoading();

    fetch('/chatbot/send/', {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken')},
        body: form
    })
    .then(r => r.json())
    .then(data => {
        removeLoading(loading);
        if (data.error) { addSystem(data.error); return; }
        if (data.session_uuid) activeUuid = data.session_uuid;
        if (data.conversation_id) activeConversationId = data.conversation_id;
        appendMessage('bot', data.response);
        loadConversations();
        userInput.value = '';
        fileInput.value = '';
    })
    .catch(() => {
        removeLoading(loading);
        addSystem('Network error.');
    });
}

function appendMessage(sender, text, fileUrl) {
    const el = document.createElement('div');
    el.className = 'message ' + (sender === 'user' ? 'user-message' : 'bot-message');
    let inner = `<div class="text">${formatMessage(text)}</div>`;
    if (fileUrl) inner += `<div style="margin-top:6px"><a href="${fileUrl}" target="_blank">📎 View file</a></div>`;
    el.innerHTML = inner;
    messagesContainer.appendChild(el);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addSystem(text) {
    const el = document.createElement('div');
    el.className = 'message bot-message';
    el.innerHTML = `<div class="text">${escapeHtml(text)}</div>`;
    messagesContainer.appendChild(el);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showLoading() {
    const id = 'loading-' + Date.now();
    const el = document.createElement('div');
    el.id = id;
    el.className = 'message bot-message';
    el.innerHTML = `<div class="text"><em>💭 Thinking...</em></div>`;
    messagesContainer.appendChild(el);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return id;
}
function removeLoading(id) { const el = document.getElementById(id); if (el) el.remove(); }

fileInput && fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) appendMessage('user', `📎 Uploaded: <strong>${e.target.files[0].name}</strong>`);
});

// voice input
if (audioBtn) {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        audioBtn.addEventListener('click', () => recognition.start());
        recognition.onresult = (ev) => { userInput.value = ev.results[0][0].transcript; };
    } else {
        audioBtn.style.opacity = 0.5;
        audioBtn.title = 'Speech not supported in this browser';
    }
}

// utilities
function formatMessage(text) {
    if (!text) return '';
    return text.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
               .replace(/`([^`]+)`/g, '<code>$1</code>')
               .replace(/\n/g, '<br>');
}
function fillSuggestion(text) { userInput.value = text; }

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe.replace(/[&<"'>]/g, function(m){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'})[m]; });
}

function getCookie(name) {
    const v = document.cookie.split('; ').find(row => row.startsWith(name + '='));
    return v ? decodeURIComponent(v.split('=')[1]) : null;
}

// initial load
loadConversations();
