// Student messaging functionality
class StudentChat {
    constructor() {
        this.socket = null;
        this.currentConversation = null;

        // ✅ Load studentId safely from json_script
        const studentData = JSON.parse(document.getElementById("student-data").textContent);
        this.studentId = studentData.id;

        // DOM elements
        this.conversationsContainer = document.getElementById('studentConversations');
        this.chatMessages = document.getElementById('studentChatMessages');
        this.messageInput = document.getElementById('studentMessageInput');
        this.sendButton = document.getElementById('studentSendButton');
        this.chatHeader = document.getElementById('studentChatHeader');

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
            const response = await fetch(`/api/conversations/?user_type=student&user_id=${this.studentId}`);
            const data = await response.json();
            console.log("✅ Conversations:", data);

            if (data.error) {
                this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Error loading conversations</div>`;
                return;
            }
            this.renderConversations(data.conversations);
        } catch (error) {
            console.error('Error loading conversations:', error);
            this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Failed to load conversations</div>`;
        }
    }

    renderConversations(conversations) {
        if (conversations.length === 0) {
            this.conversationsContainer.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-chat-left-text display-4"></i>
                    <p class="mt-2">No conversations yet</p>
                    <button onclick="showMentorsList()" class="btn btn-sm btn-primary mt-2">
                        Message a mentor
                    </button>
                </div>
            `;
            return;
        }

        let html = '';
        conversations.forEach(conv => {
            const lastMessageTime = new Date(conv.last_message_time).toLocaleTimeString();

            html += `
                <div class="conversation-item" data-id="${conv.id}" 
                     onclick="window.studentChat.selectConversation(${JSON.stringify(conv).replace(/"/g, '&quot;')})">
                    <div>
                        <div style="font-weight: 500;">${conv.name}</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 4px;">
                            ${conv.last_message.substring(0, 30)}${conv.last_message.length > 30 ? '...' : ''}
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
        document.querySelectorAll('.conversation-item').forEach(item => item.classList.remove('active'));
        document.querySelector(`.conversation-item[data-id="${conversation.id}"]`).classList.add('active');

        this.currentConversation = conversation;
        this.chatHeader.innerHTML = `
            <h6 class="mb-0">
                <i class="bi bi-chat-left-text me-2"></i>
                ${conversation.name}
                ${conversation.type === 'forum' ? '<span class="badge bg-info ms-2">Forum</span>' : ''}
            </h6>
        `;

        this.messageInput.disabled = false;
        this.sendButton.disabled = false;
        this.messageInput.focus();

        this.connectToConversation(conversation.id);
        await this.loadMessages(conversation.id);
    }

    connectToConversation(conversationId) {
        if (this.socket) this.socket.close();

        this.socket = new WebSocket(
            `ws://${window.location.host}/ws/chat/${conversationId}/student/${this.studentId}/`
        );

        this.socket.onmessage = (e) => this.displayMessage(JSON.parse(e.data));
        this.socket.onclose = () => console.error('Chat socket closed unexpectedly');
        this.socket.onopen = () => console.log('WebSocket connection established');
    }

    async loadMessages(conversationId) {
        try {
            const response = await fetch(`/api/messages/${conversationId}/?user_type=student&user_id=${this.studentId}`);
            const data = await response.json();

            if (data.error) {
                this.chatMessages.innerHTML = `<div class="text-center py-3 text-danger">Error loading messages</div>`;
                return;
            }

            this.chatMessages.innerHTML = '';
            if (data.messages.length === 0) {
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
                sender_type: 'student',
                sender_id: this.studentId
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

// Mentor functions
function showMentorsList() {
    fetch('/api/mentors/')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error loading mentors: ' + data.error);
                return;
            }

            const mentorsList = document.getElementById('mentorsList');
            if (data.mentors.length === 0) {
                mentorsList.innerHTML = '<div class="text-center py-3 text-muted">No mentors available</div>';
                return;
            }

            let html = '';
            data.mentors.forEach(mentor => {
                const statusClass = mentor.is_available ? 'text-success' : 'text-secondary';
                const statusText = mentor.is_available ? 'Available' : 'Not Available';

                html += `
                    <div class="mentor-item p-2 border-bottom" style="cursor: pointer;" 
                         onclick="startDmWithMentor(${mentor.id})" ${!mentor.is_available ? 'title="This mentor is currently not available"' : ''}>
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-medium">${mentor.name}</div>
                                <small class="text-muted">${mentor.email}</small>
                            </div>
                            <div class="${statusClass} small">
                                <i class="bi bi-circle-fill"></i> ${statusText}
                            </div>
                        </div>
                    </div>
                `;
            });

            mentorsList.innerHTML = html;
            new bootstrap.Modal(document.getElementById('mentorsModal')).show();
        })
        .catch(error => {
            console.error('Error loading mentors:', error);
            document.getElementById('mentorsList').innerHTML = '<div class="text-center py-3 text-danger">Failed to load mentors</div>';
        });
}

function closeMentorsModal() {
    bootstrap.Modal.getInstance(document.getElementById('mentorsModal')).hide();
}

function startDmWithMentor(mentorId) {
    const studentData = JSON.parse(document.getElementById("student-data").textContent);
    const studentId = studentData.id;

    console.log("🚀 Sending:", { student_id: studentId, mentor_id: mentorId });

    fetch('/api/start_dm/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, mentor_id: mentorId }),
    })
    .then(response => response.json())
    .then(data => {
        console.log("✅ Response:", data);
        if (data.error) {
            alert('Error starting conversation: ' + data.error);
            return;
        }
        closeMentorsModal();
        if (window.studentChat) {
            window.studentChat.loadConversations();
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

function filterConversations(searchTerm) {
    const items = document.querySelectorAll('.conversation-item');
    searchTerm = searchTerm.toLowerCase();

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(searchTerm) ? 'flex' : 'none';
    });
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.studentChat = new StudentChat();
});
