// Mentor messaging functionality
class MentorChat {
    constructor() {
        this.socket = null;
        this.currentConversation = null;

        // mentorId injected from template context
        this.mentorId = "{{ admininfo.id }}";  

        // DOM elements
        this.conversationsContainer = document.getElementById('mentorConversations');
        this.chatMessages = document.getElementById('mentorChatMessages');
        this.messageInput = document.getElementById('mentorMessageInput');
        this.sendButton = document.getElementById('mentorSendButton');
        this.chatHeader = document.getElementById('mentorChatHeader');

        // Event listeners
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // Initialize
        this.loadConversations();
    }

    async loadConversations() {
        try {
            const response = await fetch(`/api/conversations/?user_type=mentor&user_id=${this.mentorId}`);
            const data = await response.json();
            console.log("✅ Mentor Conversations:", data);

            if (data.error) {
                this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Error loading conversations</div>`;
                return;
            }
            this.renderConversations(data.conversations);
        } catch (error) {
            console.error('Error loading mentor conversations:', error);
            this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Failed to load conversations</div>`;
        }
    }

    renderConversations(conversations) {
        if (!conversations || conversations.length === 0) {
            this.conversationsContainer.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-chat-left-text display-4"></i>
                    <p class="mt-2">No conversations yet</p>
                    <button onclick="showStudentsList()" class="btn btn-sm btn-primary mt-2">
                        Start a conversation
                    </button>
                </div>
            `;
            return;
        }

        let html = '';
        conversations.forEach(conv => {
            const lastMessageTime = conv.last_message_time
                ? new Date(conv.last_message_time).toLocaleTimeString()
                : '';

            html += `
                <div class="conversation-item" data-id="${conv.id}" 
                     onclick="window.mentorChat.selectConversation(${JSON.stringify(conv).replace(/"/g, '&quot;')})">
                    <div>
                        <div style="font-weight: 500;">${conv.name}</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 4px;">
                            ${conv.last_message ? conv.last_message.substring(0, 30) : ''}${conv.last_message && conv.last_message.length > 30 ? '...' : ''}
                        </div>
                        <div style="font-size: 0.8em; color: #999; margin-top: 2px;">${lastMessageTime}</div>
                    </div>
                    ${conv.unread_count > 0 ? `
                        <span style="background: #007bff; color: white; border-radius: 50%;
                                     width: 20px; height: 20px; display: flex;
                                     align-items: center; justify-content: center; font-size: 0.8em;">
                            ${conv.unread_count}
                        </span>
                    ` : ''}
                </div>
            `;
        });

        this.conversationsContainer.innerHTML = html;
    }

    async selectConversation(conversation) {
        // Reset active class
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`.conversation-item[data-id="${conversation.id}"]`).classList.add('active');

        this.currentConversation = conversation;
        this.chatHeader.innerHTML = `
            <h6 class="mb-0">
                <i class="bi bi-chat-left-text me-2"></i>
                ${conversation.name}
                ${conversation.type === 'forum' ? '<span class="badge bg-info ms-2">Forum</span>' : ''}
            </h6>
        `;

        // Enable chat input
        this.messageInput.disabled = false;
        this.sendButton.disabled = false;
        this.messageInput.focus();

        // Connect to WebSocket
        this.connectToConversation(conversation.id);

        // Load conversation messages
        await this.loadMessages(conversation.id);
    }

    connectToConversation(conversationId) {
        if (this.socket) this.socket.close();

        this.socket = new WebSocket(
            `ws://${window.location.host}/ws/chat/${conversationId}/mentor/${this.mentorId}/`
        );

        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.displayMessage(data);
        };

        this.socket.onopen = () => {
            console.log(`✅ WebSocket connected (Conversation ${conversationId})`);
        };

        this.socket.onclose = () => {
            console.error(`❌ WebSocket closed for conversation ${conversationId}`);
        };
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
                    </div>
                `;
            } else {
                data.messages.forEach(msg => this.displayMessage(msg));
                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            this.chatMessages.innerHTML = `<div class="text-center py-3 text-danger">Failed to load messages</div>`;
        }
    }

    sendMessage() {
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
        if (this.chatMessages.querySelector('.text-muted')) {
            this.chatMessages.innerHTML = '';
        }

        const messageElement = document.createElement('div');
        messageElement.className = `message ${data.is_own ? 'own-message' : 'other-message'}`;

        const timestamp = new Date(data.timestamp).toLocaleTimeString();

        messageElement.innerHTML = `
            ${!data.is_own ? `<div class="message-sender">${data.sender_name}</div>` : ''}
            <div>${data.message}</div>
            <div class="message-time">${timestamp}</div>
        `;

        this.chatMessages.appendChild(messageElement);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

// ================= Global mentor functions ==================

function showStudentsList() {
    fetch('/api/students/')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error loading students: ' + data.error);
                return;
            }

            const studentsList = document.getElementById('studentsList');
            if (!data.students || data.students.length === 0) {
                studentsList.innerHTML = '<div class="text-center py-3 text-muted">No students available</div>';
                return;
            }

            let html = '';
            data.students.forEach(student => {
                html += `
                    <div class="student-item p-2 border-bottom" style="cursor: pointer;" 
                         onclick="startDmWithStudent(${student.id})">
                        <div class="fw-medium">${student.name}</div>
                        <small class="text-muted">${student.email}</small>
                    </div>
                `;
            });
            studentsList.innerHTML = html;

            new bootstrap.Modal(document.getElementById('studentsModal')).show();
        })
        .catch(error => {
            console.error('Error loading students:', error);
            document.getElementById('studentsList').innerHTML = '<div class="text-center py-3 text-danger">Failed to load students</div>';
        });
}

function closeStudentsModal() {
    bootstrap.Modal.getInstance(document.getElementById('studentsModal')).hide();
}

function startDmWithStudent(studentId) {
    const mentorId = "{{ admininfo.id }}";

    fetch('/api/start_dm/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, mentor_id: mentorId }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error starting conversation: ' + data.error);
            return;
        }

        closeStudentsModal();
        if (window.mentorChat) {
            window.mentorChat.loadConversations();
            setTimeout(() => {
                const newConvElement = document.querySelector(`.conversation-item[data-id="${data.conversation_id}"]`);
                if (newConvElement) newConvElement.click();
            }, 500);
        }
    })
    .catch(error => {
        console.error('Error starting DM:', error);
        alert('Failed to start conversation');
    });
}

function createNewForum() {
    document.getElementById('forumName').value = '';
    document.getElementById('forumMessage').value = '';
    new bootstrap.Modal(document.getElementById('forumModal')).show();
}

function closeForumModal() {
    bootstrap.Modal.getInstance(document.getElementById('forumModal')).hide();
}

function submitForum() {
    const name = document.getElementById('forumName').value;
    const message = document.getElementById('forumMessage').value;
    const mentorId = "{{ admininfo.id }}";

    if (!name || !message) {
        alert('Please enter both forum name and initial message');
        return;
    }

    fetch('/api/create_forum/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, content: message, mentor_id: mentorId }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error creating forum: ' + data.error);
            return;
        }

        closeForumModal();
        if (window.mentorChat) window.mentorChat.loadConversations();
        alert('Forum created successfully!');
    })
    .catch(error => {
        console.error('Error creating forum:', error);
        alert('Failed to create forum');
    });
}

function filterConversations(searchTerm) {
    const items = document.querySelectorAll('.conversation-item');
    searchTerm = searchTerm.toLowerCase();

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(searchTerm) ? 'flex' : 'none';
    });
}

// Initialize mentor chat
document.addEventListener('DOMContentLoaded', () => {
    window.mentorChat = new MentorChat();
});
