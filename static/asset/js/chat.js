/* ---------- helper functions ---------- */
function getMentorData() {
  const el = document.getElementById("mentor-data");
  if (!el) return null;
  try { return JSON.parse(el.textContent); } catch(e) { console.error("mentor-data parse error", e); return null; }
}

function getCookie(name) {
  // standard Django cookie helper
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function waitForSelector(selector, timeout = 4000) {
  return new Promise((resolve, reject) => {
    const el = document.querySelector(selector);
    if (el) return resolve(el);

    const observer = new MutationObserver(() => {
      const found = document.querySelector(selector);
      if (found) {
        observer.disconnect();
        clearTimeout(timer);
        resolve(found);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    const timer = setTimeout(() => {
      observer.disconnect();
      reject(new Error("timeout waiting for " + selector));
    }, timeout);
  });
}

/* ---------- Mentor messaging functionality (updated) ---------- */
class MentorChat {
  constructor() {
    this.socket = null;
    this.currentConversation = null;

    const mentorData = getMentorData();
    if (!mentorData) {
      console.error("mentor-data missing or invalid");
      this.mentorId = null;
    } else {
      this.mentorId = mentorData.id;
    }

    // DOM elements
    this.conversationsContainer = document.getElementById('mentorConversations');
    this.chatMessages = document.getElementById('mentorChatMessages');
    this.messageInput = document.getElementById('mentorMessageInput');
    this.sendButton = document.getElementById('mentorSendButton');
    this.chatHeader = document.getElementById('mentorChatHeader');

    // listeners (guard in case inputs don't exist yet)
    if (this.sendButton) this.sendButton.addEventListener('click', () => this.sendMessage());
    if (this.messageInput) this.messageInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') this.sendMessage(); });

    // Initialize
    if (this.mentorId) this.loadConversations();
  }

  async loadConversations() {
    if (!this.mentorId) return;
    try {
      const response = await fetch(`/api/conversations/?user_type=mentor&user_id=${this.mentorId}`);
      const data = await response.json();
      console.log("✅ Mentor Conversations:", data);

      if (data.error) {
        this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Error loading conversations</div>`;
        return;
      }
      this.renderConversations(data.conversations || []);
    } catch (error) {
      console.error('Error loading conversations:', error);
      if (this.conversationsContainer) this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Failed to load conversations</div>`;
    }
  }

  renderConversations(conversations) {
    if (!this.conversationsContainer) return;
    if (!conversations || conversations.length === 0) {
      this.conversationsContainer.innerHTML = `
        <div class="text-center py-4 text-muted">
          <i class="bi bi-chat-left-text display-4"></i>
          <p class="mt-2">No conversations yet</p>
          <button onclick="showStudentsList()" class="btn btn-sm btn-primary mt-2">Message a student</button>
        </div>`;
      return;
    }

    let html = '';
    conversations.forEach(conv => {
      const lastMessageTime = conv.last_message_time ? (new Date(conv.last_message_time)).toLocaleTimeString() : '';
      const lastMessage = conv.last_message || '';
      const snippet = lastMessage.substring(0, 30) + (lastMessage.length > 30 ? '...' : '');

      // Build data attribute and onclick with safe JSON (replace quotes)
      const convJson = JSON.stringify(conv).replace(/"/g, '&quot;');

      html += `
        <div class="conversation-item d-flex justify-content-between align-items-start py-2 px-2" data-id="${conv.id}"
             onclick="window.mentorChat.selectConversation(${convJson})" style="cursor:pointer;">
          <div>
            <div style="font-weight:500;">${conv.name}</div>
            <div style="font-size:0.9em; color:#666; margin-top:4px;">${snippet}</div>
            <div style="font-size:0.8em; color:#999; margin-top:2px;">${lastMessageTime}</div>
          </div>
          ${conv.unread_count && conv.unread_count > 0 ? `
            <span style="background:#007bff; color:#fff; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.8em;">
              ${conv.unread_count}
            </span>` : ''}
        </div>
      `;
    });

    this.conversationsContainer.innerHTML = html;
  }

  async selectConversation(conversation) {
    // Remove active from all then set on the selected (if exists)
    document.querySelectorAll('.conversation-item').forEach(item => item.classList.remove('active'));
    const itemEl = document.querySelector(`.conversation-item[data-id="${conversation.id}"]`);
    if (itemEl) itemEl.classList.add('active');

    this.currentConversation = conversation;
    this.chatHeader.innerHTML = `
      <h6 class="mb-0">
        <i class="bi bi-chat-left-text me-2"></i>
        ${conversation.name || 'Conversation'}
        ${conversation.type === 'forum' ? '<span class="badge bg-info ms-2">Forum</span>' : ''}
      </h6>`;

    if (this.messageInput) { this.messageInput.disabled = false; this.messageInput.focus(); }
    if (this.sendButton) this.sendButton.disabled = false;

    // Connect to websocket and load messages
    this.connectToConversation(conversation.id);
    await this.loadMessages(conversation.id);
  }

  connectToConversation(conversationId) {
    if (!this.mentorId) { console.error("mentorId missing for websocket"); return; }
    if (this.socket) {
      try { this.socket.close(); } catch(e) {}
    }

    const proto = (window.location.protocol === 'https:') ? 'wss' : 'ws';
    const url = `${proto}://${window.location.host}/ws/chat/${conversationId}/mentor/${this.mentorId}/`;
    console.log("Opening websocket:", url);

    try {
      this.socket = new WebSocket(url);
    } catch (err) {
      console.error("WebSocket construct error:", err);
      return;
    }

    this.socket.onopen = () => console.log('WebSocket opened:', url);
    this.socket.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        this.displayMessage({
          message: data.message,
          sender_name: data.sender_name,
          timestamp: data.timestamp,
          is_own: data.is_own
        });
      } catch (err) { console.error("WS message parse error", err); }
    };
    this.socket.onerror = (err) => console.error('WebSocket error', err);
    this.socket.onclose = (ev) => console.warn('WebSocket closed', ev);
  }

  async loadMessages(conversationId) {
    try {
      const response = await fetch(`/api/messages/${conversationId}/?user_type=mentor&user_id=${this.mentorId}`);
      const data = await response.json();

      if (data.error) {
        this.chatMessages.innerHTML = `<div class="text-center py-3 text-danger">Error loading messages</div>`;
        return;
      }

      this.chatMessages.innerHTML = '';
      if (!data.messages || data.messages.length === 0) {
        this.chatMessages.innerHTML = `
          <div class="text-center py-4 text-muted">
            <i class="bi bi-chat-left-text display-4"></i>
            <p class="mt-2">No messages yet</p>
            <p class="small">Start the conversation by sending a message</p>
          </div>`;
      } else {
        data.messages.forEach(msg => this.displayMessage({
          message: msg.content || msg.message || msg,
          sender_name: msg.sender_name,
          timestamp: msg.timestamp,
          is_own: !!msg.is_own
        }));
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
      }
    } catch (error) {
      console.error('Error loading messages:', error);
      if (this.chatMessages) this.chatMessages.innerHTML = `<div class="text-center py-3 text-danger">Failed to load messages</div>`;
    }
  }

  sendMessage() {
    if (!this.messageInput) return;
    const message = this.messageInput.value.trim();
    if (!message) return;

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        message: message,
        sender_type: 'mentor',
        sender_id: this.mentorId
      }));
      this.messageInput.value = '';
    } else {
      alert('Connection error. Please try again.');
    }
  }

  displayMessage(data) {
    if (!this.chatMessages) return;
    // remove placeholder text if present
    if (this.chatMessages.querySelector('.text-muted')) this.chatMessages.innerHTML = '';

    const messageElement = document.createElement('div');
    messageElement.className = `message ${data.is_own ? 'own-message' : 'other-message'} mb-2`;

    const timestamp = data.timestamp ? (new Date(data.timestamp)).toLocaleTimeString() : '';

    messageElement.innerHTML = `
      ${!data.is_own ? `<div class="message-sender fw-semibold">${data.sender_name || ''}</div>` : ''}
      <div class="message-body">${data.message}</div>
      <div class="message-time small text-muted">${timestamp}</div>
    `;

    this.chatMessages.appendChild(messageElement);
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }
}

/* ---------- student list + start DM (updated) ---------- */

async function showStudentsList() {
  try {
    const resp = await fetch('/api/students/');
    const data = await resp.json();
    const studentsList = document.getElementById('studentsList');

    if (!studentsList) return;
    if (data.error) {
      studentsList.innerHTML = '<div class="text-center py-3 text-danger">Error loading students</div>';
      return;
    }

    if (!data.students || data.students.length === 0) {
      studentsList.innerHTML = '<div class="text-center py-3 text-muted">No students available</div>';
      return;
    }

    let html = '';
    data.students.forEach(student => {
      html += `
        <div class="student-item p-2 border-bottom" style="cursor:pointer;" onclick="startDmWithStudent(${student.id})">
          <div class="fw-medium">${student.name}</div>
          <small class="text-muted">${student.email || ''}</small>
        </div>
      `;
    });
    studentsList.innerHTML = html;
    new bootstrap.Modal(document.getElementById('studentsModal')).show();
  } catch (err) {
    console.error('Error loading students:', err);
    const studentsList = document.getElementById('studentsList');
    if (studentsList) studentsList.innerHTML = '<div class="text-center py-3 text-danger">Failed to load students</div>';
  }
}

function closeStudentsModal() {
  const modal = document.getElementById('studentsModal');
  const inst = bootstrap.Modal.getInstance(modal);
  if (inst) inst.hide();
}

async function startDmWithStudent(studentId) {
  const mentorData = getMentorData();
  if (!mentorData || !mentorData.id) { alert('Mentor not identified'); return; }
  const mentorId = mentorData.id;

  try {
    const resp = await fetch('/api/start_dm/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({ mentor_id: mentorId, student_id: studentId })
    });

    const data = await resp.json();
    console.log("Start DM response:", data);

    if (data.error) {
      alert('Error starting conversation: ' + data.error);
      return;
    }
    if (!data.conversation_id) {
      alert('Failed to start conversation: no conversation_id returned');
      return;
    }

    // Close modal and refresh conversations, then open the new conversation
    closeStudentsModal();

    if (window.mentorChat) {
      await window.mentorChat.loadConversations();

      try {
        const selector = `.conversation-item[data-id="${data.conversation_id}"]`;
        const el = await waitForSelector(selector, 3000);
        el.click();
      } catch (err) {
        // fallback: directly attempt to open by id (selectConversation requires a conversation object)
        try {
          window.mentorChat.selectConversation({ id: data.conversation_id, name: 'Conversation' });
        } catch (e) {
          console.warn('Could not auto-open conversation:', e);
        }
      }
    }
  } catch (err) {
    console.error('Error starting DM:', err);
    alert('Failed to start conversation');
  }
}

/* ---------- search filter ---------- */
function filterConversations(searchTerm) {
  const items = document.querySelectorAll('.conversation-item');
  searchTerm = (searchTerm || '').toLowerCase();
  items.forEach(item => {
    const text = (item.textContent || '').toLowerCase();
    item.style.display = text.includes(searchTerm) ? 'flex' : 'none';
  });
}

/* ---------- init ---------- */
document.addEventListener('DOMContentLoaded', () => {
  window.mentorChat = new MentorChat();
});
