// chatbot/script.js
// Full feature chat frontend: load conversations, open/send messages, multi-select clear with modal,
// and auto-dismissing notifications (5s).

// -------------------- Element references --------------------
const messagesContainer = document.getElementById('messagesContainer');
const chatSessionsEl = document.getElementById('chatSessions');
const userInput = document.getElementById('userInput');
const fileInput = document.getElementById('fileInput');
const audioBtn = document.getElementById('audioBtn');
const sendBtn = document.getElementById('sendBtn');
const btnNewChat = document.getElementById('btnNewChat');
const clearChatBtn = document.getElementById('clearChatBtn');

const chatSelectList = document.getElementById('chatSelectList');
const selectAllChats = document.getElementById('selectAllChats');
const confirmClearBtn = document.getElementById('confirmClearChatBtn');

// active conversation UUID (session_uuid). Start null so UI shows placeholder.
let activeUuid = null;
let activeConversationId = null;

// -------------------- Utility / UI helpers --------------------
function escapeHtml(s) {
    if (!s) return '';
    return s.replace(/[&<"'>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'})[m]);
}

function formatMessage(text) {
    if (!text) return '';
    return escapeHtml(text)
        .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

function showPlaceholderMessage(text = 'Select a chat to start') {
    messagesContainer.innerHTML = `<div class="message bot-message placeholder"><div class="text text-muted">${escapeHtml(text)}</div></div>`;
}

function showSidebarPlaceholder() {
    chatSessionsEl.innerHTML = `<div class="session-item text-muted">No chats yet. Click New Chat.</div>`;
}

function showLoadingBubble() {
    const id = 'loading-' + Date.now();
    const el = document.createElement('div');
    el.id = id;
    el.className = 'message bot-message';
    el.innerHTML = '<div class="text"><em>💭 Thinking...</em></div>';
    messagesContainer.appendChild(el);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return id;
}

function removeLoadingBubble(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
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
    el.innerHTML = `<div class="text text-muted">${escapeHtml(text)}</div>`;
    messagesContainer.appendChild(el);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Toast-like notification (top-right). disappears after 5s
function showNotification(type = 'info', message = '') {
    // create container if missing
    let container = document.getElementById('sb-notify-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'sb-notify-container';
        container.style.position = 'fixed';
        container.style.top = '18px';
        container.style.right = '18px';
        container.style.zIndex = 10800;
        document.body.appendChild(container);
    }

    const el = document.createElement('div');
    el.className = 'sb-notify';
    el.style.minWidth = '240px';
    el.style.marginTop = '8px';
    el.style.padding = '10px 12px';
    el.style.borderRadius = '8px';
    el.style.boxShadow = '0 6px 18px rgba(0,0,0,0.12)';
    el.style.color = '#fff';
    el.style.fontSize = '14px';
    el.style.opacity = '0';
    el.style.transition = 'all 220ms ease';

    if (type === 'success') {
        el.style.background = 'linear-gradient(90deg,#1e7e34,#28a745)';
    } else if (type === 'error') {
        el.style.background = 'linear-gradient(90deg,#a71d2a,#dc3545)';
    } else {
        el.style.background = 'linear-gradient(90deg,#0d6efd,#3b82f6)';
    }

    el.innerHTML = `<strong style="display:block;margin-bottom:4px">${escapeHtml(message)}</strong>`;

    container.prepend(el);

    // fade in
    requestAnimationFrame(() => { el.style.opacity = '1'; el.style.transform = 'translateY(0)'; });

    // remove after 5s
    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(-6px)';
        setTimeout(() => el.remove(), 260);
    }, 5000);
}

// CSRF helper (Django cookie)
function getCookie(name) {
    const v = document.cookie.split('; ').find(row => row.startsWith(name + '='));
    return v ? decodeURIComponent(v.split('=')[1]) : null;
}

// -------------------- Conversations (sidebar) --------------------
function loadConversations() {
    fetch('/chatbot/conversations/')
        .then(r => {
            if (!r.ok) throw new Error('Failed to fetch conversations');
            return r.json();
        })
        .then(data => {
            chatSessionsEl.innerHTML = '';
            const list = data.conversations || [];
            if (!list.length) {
                showSidebarPlaceholder();
                showPlaceholderMessage('No chats yet — create one with "New Chat"');
                return;
            }

            // build elements
            list.forEach((s, i) => {
                const div = document.createElement('div');
                div.className = 'session-item';
                div.dataset.uuid = s.uuid;
                div.dataset.convid = s.id;
                div.style.cursor = 'pointer';
                div.innerHTML = `<strong>${escapeHtml(s.title)}</strong>
                                 <div style="font-size:12px;color:#9fb9c3;margin-top:6px">${escapeHtml(s.snippet)}</div>`;
                div.addEventListener('click', () => {
                    setActiveSessionInUI(div);
                    openConversation(s.uuid);
                });
                chatSessionsEl.appendChild(div);
            });

            // if none active, pick first automatically
            if (!activeUuid) {
                const first = chatSessionsEl.querySelector('.session-item');
                if (first) {
                    setActiveSessionInUI(first);
                    openConversation(first.dataset.uuid);
                } else {
                    showPlaceholderMessage('Select a chat to start');
                }
            }
        })
        .catch(err => {
            console.error('Could not load conversations', err);
            chatSessionsEl.innerHTML = '<div class="session-item text-muted">Could not load conversations.</div>';
            showPlaceholderMessage('Unable to load chats');
        });
}

function setActiveSessionInUI(elem) {
    // remove previous active class
    document.querySelectorAll('.session-item.active').forEach(n => n.classList.remove('active'));
    if (elem) elem.classList.add('active');
}

// -------------------- Open a conversation --------------------
function openConversation(uuid) {
    if (!uuid) {
        showPlaceholderMessage('Select a chat to start');
        return;
    }
    activeUuid = uuid;
    messagesContainer.innerHTML = '<div class="message bot-message"><div class="text">Loading…</div></div>';

    fetch(`/chatbot/messages/?uuid=${encodeURIComponent(uuid)}`)
        .then(r => {
            if (!r.ok) throw new Error('Failed to load messages');
            return r.json();
        })
        .then(data => {
            messagesContainer.innerHTML = '';
            if (data.error) {
                addSystem(data.error || 'No messages');
                return;
            }
            if (!data.messages || !data.messages.length) {
                addSystem('No messages yet. Say hi 👋');
            } else {
                data.messages.forEach(m => appendMessage(m.sender, m.text, m.file));
            }
            if (data.conversation) activeConversationId = data.conversation.id;
        })
        .catch(err => {
            console.error('openConversation error', err);
            messagesContainer.innerHTML = '';
            addSystem('Failed to load conversation');
            showNotification('error', 'Failed to load messages');
        });
}

// -------------------- Create new conversation --------------------
if (btnNewChat) {
    btnNewChat.addEventListener('click', () => {
        fetch('/chatbot/create/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        })
        .then(r => {
            if (!r.ok) throw new Error('Could not create conversation');
            return r.json();
        })
        .then(data => {
            if (data.session_uuid) {
                activeUuid = data.session_uuid;
                // refresh sidebar then open
                loadConversations();
                openConversation(data.session_uuid);
                showNotification('success', 'New chat created');
            } else {
                showNotification('error', 'Could not create conversation');
            }
        })
        .catch(err => {
            console.error('create conversation error', err);
            showNotification('error', 'Failed to create chat');
        });
    });
}

// -------------------- Send message --------------------
function sendMessage() {
    const text = (userInput && userInput.value) ? userInput.value.trim() : '';
    const file = (fileInput && fileInput.files && fileInput.files[0]) ? fileInput.files[0] : null;
    if (!text && !file) return;

    if (text) appendMessage('user', text);

    const form = new FormData();
    if (text) form.append('message', text);
    if (activeUuid) form.append('session_uuid', activeUuid);
    if (file) form.append('file', file);

    const loadingId = showLoadingBubble();

    fetch('/chatbot/send/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: form
    })
    .then(r => r.json())
    .then(data => {
        removeLoadingBubble(loadingId);
        if (data.error) {
            addSystem(data.error);
            showNotification('error', data.error);
            return;
        }
        if (data.session_uuid) activeUuid = data.session_uuid;
        if (data.conversation_id) activeConversationId = data.conversation_id;
        appendMessage('bot', data.response || '...');

        // refresh sidebar to update snippets/times
        loadConversations();

        // clear input
        if (userInput) userInput.value = '';
        if (fileInput) fileInput.value = '';
    })
    .catch(err => {
        removeLoadingBubble(loadingId);
        console.error('sendMessage error', err);
        addSystem('Network error sending message.');
        showNotification('error', 'Failed to send message');
    });
}

if (sendBtn) sendBtn.addEventListener('click', sendMessage);
if (userInput) userInput.addEventListener('keypress', e => { if (e.key === 'Enter') sendMessage(); });

// -------------------- Clear chats (multi-select) --------------------
if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
        const modalEl = document.getElementById('clearChatModal');
        if (!modalEl) {
            console.error('Clear chat modal not found');
            showNotification('error', 'Clear chat modal missing');
            return;
        }

        // reset list
        if (chatSelectList) chatSelectList.innerHTML = '';

        // populate from current sidebar items
        const items = Array.from(document.querySelectorAll('.session-item'));
        if (!items.length) {
            // show a message inside modal if none
            if (chatSelectList) chatSelectList.innerHTML = '<div class="text-muted">No conversations available to clear.</div>';
        } else {
            items.forEach(item => {
                const uuid = item.dataset.uuid;
                const titleEl = item.querySelector('strong');
                const title = titleEl ? titleEl.innerText : (item.innerText || 'Chat');
                const safeId = uuid ? uuid.replace(/[^a-zA-Z0-9-]/g, '') : Math.random().toString(36).slice(2);

                const div = document.createElement('div');
                div.className = 'form-check mb-1';
                div.style.padding = '6px 4px';
                div.innerHTML = `
                    <input class="form-check-input chat-checkbox" type="checkbox" value="${uuid}" id="chat-${safeId}">
                    <label class="form-check-label" for="chat-${safeId}" style="margin-left:8px">${escapeHtml(title)}</label>
                `;
                chatSelectList.appendChild(div);
            });
        }

        // reset select all
        if (selectAllChats) selectAllChats.checked = false;

        // show modal
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    });
}

if (selectAllChats) {
    selectAllChats.addEventListener('change', () => {
        const checked = selectAllChats.checked;
        document.querySelectorAll('.chat-checkbox').forEach(cb => cb.checked = checked);
    });
}

if (confirmClearBtn) {
    confirmClearBtn.addEventListener('click', () => {
        // collect selected uuids
        const selectedUuids = Array.from(document.querySelectorAll('.chat-checkbox:checked')).map(cb => cb.value).filter(Boolean);
        if (!selectedUuids.length) {
            showNotification('error', 'Please select at least one chat to clear');
            return;
        }

        // POST to backend (expects { uuids: [...] })
        fetch('/chatbot/api/clear_chats/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ uuids: selectedUuids })
        })
        .then(r => {
            if (!r.ok) throw new Error('Server error during clear');
            return r.json();
        })
        .then(data => {
            if (data.success) {
                // remove cleared items from sidebar
                selectedUuids.forEach(uuid => {
                    const el = document.querySelector(`.session-item[data-uuid="${uuid}"]`);
                    if (el) el.remove();
                });

                // if active was removed, clear messages area
                if (selectedUuids.includes(activeUuid)) {
                    activeUuid = null;
                    activeConversationId = null;
                    showPlaceholderMessage('Select a chat to start');
                }

                // hide modal
                const modalEl = document.getElementById('clearChatModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();

                showNotification('success', data.message || 'Selected chats cleared');
            } else {
                showNotification('error', data.error || 'Failed to clear chats');
            }
        })
        .catch(err => {
            console.error('clear_chats error', err);
            showNotification('error', 'Error clearing chats');
        });
    });
}

// -------------------- Initial boot --------------------
(function init() {
    // show defaults while loading
    showSidebarPlaceholder();
    showPlaceholderMessage('Loading chats…');

    // load conversations and open first if any
    loadConversations();
})();
