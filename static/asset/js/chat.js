/* ---------- Helper functions ---------- */
function getMentorData() {
  const el = document.getElementById("mentor-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent);
  } catch (e) {
    console.error("mentor-data parse error", e);
    return null;
  }
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + "=")) {
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
    const obs = new MutationObserver(() => {
      const found = document.querySelector(selector);
      if (found) {
        obs.disconnect();
        clearTimeout(timer);
        resolve(found);
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
    const timer = setTimeout(() => {
      obs.disconnect();
      reject("timeout " + selector);
    }, timeout);
  });
}

/* ---------- Mentor Chat Class ---------- */
class MentorChat {
  constructor() {
    this.socket = null;
    this.currentConversation = null;
    this.conversationHistory = {};
    this.page = {};

    const mentorData = getMentorData();
    this.mentorId = mentorData?.id || null;

    // DOM elements
    this.conversationsContainer = document.getElementById("mentorConversations");
    this.chatMessages = document.getElementById("mentorChatMessages");
    this.messageInput = document.getElementById("mentorMessageInput");
    this.sendButton = document.getElementById("mentorSendButton");
    this.chatHeader = document.getElementById("mentorChatHeader");
    this.totalUnreadBadge = document.getElementById("totalUnreadBadge");

    if (this.sendButton)
      this.sendButton.addEventListener("click", () => this.sendMessage());
    if (this.messageInput)
      this.messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") this.sendMessage();
      });

    // infinite scroll for older messages
    if (this.chatMessages) {
      this.chatMessages.addEventListener("scroll", () => {
        if (this.chatMessages.scrollTop === 0) {
          this.loadOlderMessages();
        }
      });
    }

    if (this.mentorId) this.loadConversations();
  }

  async loadConversations() {
    if (!this.mentorId) return;
    try {
      const resp = await fetch(
        `/api/conversations/?user_type=mentor&user_id=${this.mentorId}`
      );
      const data = await resp.json();
      if (data.error) {
        this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Error loading conversations</div>`;
        return;
      }
      this.renderConversations(data.conversations || []);
      this.updateUnreadBadge(data.conversations || []);
    } catch (err) {
      console.error(err);
      this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Failed to load conversations</div>`;
    }
  }

  refreshConversations() {
    this.loadConversations();
  }

  updateUnreadBadge(conversations) {
    if (!this.totalUnreadBadge) return;
    const total = conversations.reduce(
      (acc, c) => acc + (c.unread_count || 0),
      0
    );
    this.totalUnreadBadge.textContent = total > 0 ? total : "";
  }

  renderConversations(conversations) {
    if (!this.conversationsContainer) return;

    if (conversations.length === 0) {
      this.conversationsContainer.innerHTML = `
        <div class="text-center py-4 text-muted">No conversations yet</div>`;
      return;
    }

    let html = "";

    const colorPalette = [
      "#007bff", "#28a745", "#ffc107", "#17a2b8",
      "#6f42c1", "#e83e8c", "#fd7e14", "#20c997",
      "#6610f2", "#d63384", "#0dcaf0", "#198754"
    ];

    conversations.forEach((c, index) => {
      const snippet =
        (c.last_message || "").substring(0, 30) +
        ((c.last_message || "").length > 30 ? "..." : "");
      const lastTime = c.last_message_time
        ? new Date(c.last_message_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : "";

      // Check for forum type - try multiple possible property names
      const isForum = c.conversation_type === "forum" || c.type === "forum" || c.is_forum === true;
      let color;
      
      if (isForum) {
        // For forums, generate color based on conversation ID for consistency
        const colorIndex = (c.id % colorPalette.length);
        color = colorPalette[colorIndex];
      } else {
        // For DMs, generate color based on conversation name for consistency
        const colorIndex = (c.name?.charCodeAt(0) || 0) % colorPalette.length;
        color = colorPalette[colorIndex];
      }

      // Forum icon with unique color or first letter avatar for DMs
      const iconHTML = isForum
        ? `<div class="rounded-circle d-flex align-items-center justify-content-center"
             style="background-color:${color};width:40px;height:40px;">
             <i class="bi bi-people-fill text-white"></i>
           </div>`
        : `<div class="rounded-circle d-flex align-items-center justify-content-center fw-bold text-white"
             style="background-color:${color};width:40px;height:40px;font-size:18px;">
             ${c.name ? c.name.charAt(0).toUpperCase() : "?"}
           </div>`;

      html += `
        <div class="conversation-item d-flex justify-content-between align-items-start py-2 px-2" 
             data-id="${c.id}" style="cursor:pointer;">
          <div class="d-flex align-items-center flex-grow-1"
               onclick="window.mentorChat.selectConversation(${JSON.stringify(c).replace(/"/g, "&quot;")})">

            ${iconHTML}

            <div class="ms-2">
              <div class="fw-medium">${c.name || "Unnamed"}</div>
              <div class="small text-muted">${snippet || "No messages yet"}</div>
              <div class="small text-secondary">${lastTime}</div>
            </div>
          </div>
        </div>`;
    });

    this.conversationsContainer.innerHTML = html;
  }

  async selectConversation(conv) {
    document
      .querySelectorAll(".conversation-item")
      .forEach((el) => el.classList.remove("active"));
    const el = document.querySelector(`.conversation-item[data-id="${conv.id}"]`);
    if (el) el.classList.add("active");

    this.currentConversation = conv;
    this.page[conv.id] = 1;
    
    // Check for forum type - try multiple possible property names
    const isForum = conv.conversation_type === "forum" || conv.type === "forum" || conv.is_forum === true;
    
    this.chatHeader.innerHTML = `
      <h6 class="mb-0">
        <i class="bi ${isForum ? 'bi-people-fill' : 'bi-chat-left-text'} me-2"></i>
        ${conv.name || "Conversation"}
        ${
          isForum
            ? '<span class="badge bg-info ms-2">Forum</span>'
            : ""
        }
      </h6>`;
    if (this.messageInput) {
      this.messageInput.disabled = false;
      this.messageInput.focus();
    }
    if (this.sendButton) this.sendButton.disabled = false;

    this.connectToConversation(conv.id);
    await this.loadMessages(conv.id, 1);
  }

  connectToConversation(convId) {
    if (!this.mentorId) return console.error("mentorId missing");
    if (this.socket)
      try {
        this.socket.close();
      } catch (e) {}
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/ws/chat/${convId}/mentor/${this.mentorId}/`;
    console.log("Connecting WS:", url);

    this.socket = new WebSocket(url);
    this.socket.onopen = () => console.log("WebSocket opened");
    this.socket.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        
        // Check for forum type - try multiple possible property names
        const isForum = this.currentConversation?.conversation_type === "forum" || 
                       this.currentConversation?.type === "forum" || 
                       this.currentConversation?.is_forum === true;
        
        this.displayMessage(
          {
            message: d.message,
            sender_name: d.sender_name,
            timestamp: d.timestamp,
            is_own: d.is_own,
            status: d.status || "sent",
            conversation_type: isForum ? "forum" : "dm"
          },
          "append"
        );
      } catch (err) {
        console.error(err);
      }
    };
    this.socket.onerror = (err) => console.error("WebSocket error", err);
    this.socket.onclose = (ev) => console.warn("WebSocket closed", ev);
  }

  async loadMessages(convId, page = 1) {
    try {
      if (page === 1) {
        this.chatMessages.innerHTML = `<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div> Loading...</div>`;
      }

      const resp = await fetch(
        `/api/messages/${convId}/?user_type=mentor&user_id=${this.mentorId}&page=${page}`
      );
      const data = await resp.json();
      if (data.error) {
        this.chatMessages.innerHTML = `<div class="text-center py-3 text-danger">Error loading messages</div>`;
        return;
      }

      if (page === 1 && !this.conversationHistory[convId])
        this.chatMessages.innerHTML = "";

      if (!data.messages || !data.messages.length) {
        if (page === 1) {
          this.chatMessages.innerHTML = `<div class="text-center py-4 text-muted">
            <i class="bi bi-chat-left-text display-4"></i>
            <p class="mt-2">No messages yet</p>
            <p class="small">Start the conversation by sending a message</p>
          </div>`;
        }
      } else {
        // Check for forum type - try multiple possible property names
        const isForum = this.currentConversation?.conversation_type === "forum" || 
                       this.currentConversation?.type === "forum" || 
                       this.currentConversation?.is_forum === true;
        
        data.messages.forEach((msg) => {
          this.displayMessage(
            {
              message: msg.content || msg.message || msg,
              sender_name: msg.sender_name,
              timestamp: msg.timestamp,
              is_own: !!msg.is_own,
              status: msg.status || "delivered",
              conversation_type: isForum ? "forum" : "dm"
            },
            page === 1 ? "append" : "prepend"
          );
        });
        if (page === 1) this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
      }
    } catch (err) {
      console.error(err);
      this.chatMessages.innerHTML = `<div class="text-center py-3 text-danger">Failed to load messages</div>`;
    }
  }

  async loadOlderMessages() {
    if (!this.currentConversation) return;
    const convId = this.currentConversation.id;
    this.page[convId] = (this.page[convId] || 1) + 1;
    const oldHeight = this.chatMessages.scrollHeight;
    await this.loadMessages(convId, this.page[convId]);
    const newHeight = this.chatMessages.scrollHeight;
    this.chatMessages.scrollTop = newHeight - oldHeight;
  }

  sendMessage() {
    if (!this.messageInput) return;
    const msg = this.messageInput.value.trim();
    if (!msg) return;
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const payload = {
        message: msg,
        sender_type: "mentor",
        sender_id: this.mentorId,
        status: "sent",
      };
      this.socket.send(JSON.stringify(payload));
      this.messageInput.value = "";
    } else {
      alert("Connection error. Please try again.");
    }
  }

  displayMessage(data, mode = "append") {
    if (!this.chatMessages) return;

    const exists = Array.from(this.chatMessages.querySelectorAll(".message")).some(
      (el) =>
        el.dataset.timestamp === data.timestamp &&
        el.dataset.sender === data.sender_name
    );
    if (exists) {
      const existing = this.chatMessages.querySelector(
        `.message[data-timestamp="${data.timestamp}"][data-sender="${data.sender_name}"]`
      );
      if (existing) {
        const statusEl = existing.querySelector(".msg-status");
        if (statusEl)
          statusEl.innerHTML = this.getStatusIcon(data.status, data.is_own);
      }
      return;
    }

    const div = document.createElement("div");
    div.className = `message mb-2 d-flex ${
      data.is_own ? "justify-content-end" : "justify-content-start"
    }`;
    div.dataset.timestamp = data.timestamp;
    div.dataset.sender = data.sender_name;

    const statusIcon = this.getStatusIcon(data.status, data.is_own);
    const isForum = data.conversation_type === "forum";
    
    // Show username for forum messages that are not our own
    const showUsername = isForum && !data.is_own;

    div.innerHTML = `<div class="${
      data.is_own ? "bg-primary text-white" : "bg-light text-dark"
    } p-2 rounded shadow-sm" style="max-width:70%;">
      ${showUsername ? `<div class="small text-muted fw-bold mb-1">${data.sender_name}</div>` : ''}
      <div>${data.message}</div>
      <div class="small ${data.is_own ? 'text-light' : 'text-muted'} text-end" style="opacity:0.8;">
        ${data.timestamp ? new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ""} 
        <span class="msg-status">${statusIcon}</span>
      </div>
    </div>`;

    if (mode === "prepend") {
      this.chatMessages.insertBefore(div, this.chatMessages.firstChild);
    } else {
      this.chatMessages.appendChild(div);
      this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    if (this.currentConversation) {
      const cid = this.currentConversation.id;
      if (!this.conversationHistory[cid]) this.conversationHistory[cid] = [];
      this.conversationHistory[cid].push(data);
    }
  }

  getStatusIcon(status, isOwn) {
    if (!isOwn) return "";
    if (status === "sent") return `<i class="bi bi-check"></i>`;
    if (status === "delivered") return `<i class="bi bi-check2-all"></i>`;
    if (status === "read")
      return `<i class="bi bi-check2-all text-primary"></i>`;
    return "";
  }
}

/* ---------- Student List + DM ---------- */
async function showStudentsList() {
  try {
    const resp = await fetch("/api/students/");
    const data = await resp.json();
    const list = document.getElementById("studentsList");
    if (!list) return;
    if (data.error) {
      list.innerHTML =
        '<div class="text-center py-3 text-danger">Error loading students</div>';
      return;
    }
    if (!data.students.length) {
      list.innerHTML =
        '<div class="text-center py-3 text-muted">No students available</div>';
      return;
    }

    let html = "";
    data.students.forEach((s) => {
      html += `<div class="student-item p-2 border-bottom d-flex align-items-center" style="cursor:pointer;" onclick="startDmWithStudent(${s.id})">
        <img src="${s.profile_image || "/static/asset/img/profile.jpeg"}" style="width:16px;height:16px;object-fit:cover;" class="rounded-circle me-2">
        <div>${s.name}</div>
      </div>`;
    });
    list.innerHTML = html;
    new bootstrap.Modal(document.getElementById("studentsModal")).show();
  } catch (err) {
    console.error(err);
    document.getElementById("studentsList").innerHTML =
      '<div class="text-center py-3 text-danger">Failed to load students</div>';
  }
}

function closeStudentsModal() {
  const modal = document.getElementById("studentsModal");
  const inst = bootstrap.Modal.getInstance(modal);
  if (inst) inst.hide();
}

async function startDmWithStudent(studentId) {
  const mentorData = getMentorData();
  if (!mentorData?.id) {
    alert("Mentor not identified");
    return;
  }
  const mentorId = mentorData.id;

  try {
    const resp = await fetch("/api/start_dm/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ mentor_id: mentorId, student_id: studentId }),
    });
    const data = await resp.json();
    if (data.error) {
      alert("Error starting conversation: " + data.error);
      return;
    }
    if (!data.conversation_id) {
      alert("No conversation created");
      return;
    }

    closeStudentsModal();
    await window.mentorChat.loadConversations();
    try {
      const el = await waitForSelector(
        `.conversation-item[data-id="${data.conversation_id}"]`,
        3000
      );
      el.click();
    } catch {
      window.mentorChat.selectConversation({
        id: data.conversation_id,
        name: "Conversation",
        conversation_type: "dm"
      });
    }
  } catch (err) {
    console.error(err);
    alert("Failed to start conversation");
  }
}

/* ---------- Filter Conversations ---------- */
function filterConversations(search) {
  const items = document.querySelectorAll(".conversation-item");
  search = (search || "").toLowerCase();
  items.forEach((i) => {
    i.style.display = (i.textContent || "").toLowerCase().includes(search)
      ? "flex"
      : "none";
  });
}

/* ---------- Initialize ---------- */
document.addEventListener("DOMContentLoaded", () => {
  window.mentorChat = new MentorChat();

  const forumForm = document.getElementById("forumForm");
  if (forumForm) {
    forumForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const name = document.getElementById("forumTitle").value.trim();
      const mentor_id = document.getElementById("mentorId").value;
      const csrftoken = getCookie("csrftoken");

      if (!name) {
        alert("Please enter a forum title.");
        return;
      }

      try {
        const response = await fetch("/create_forum/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken,
          },
          body: JSON.stringify({ name, mentor_id }),
        });

        const result = await response.json();

        if (response.ok) {
          alert("🎉 Forum created successfully!");
          const modal = bootstrap.Modal.getInstance(
            document.getElementById("createForumModal")
          );
          if (modal) modal.hide();

          forumForm.reset();
          location.reload();
        } else {
          alert(result.error || "Failed to create forum.");
        }
      } catch (err) {
        console.error(err);
        alert("Something went wrong while creating the forum.");
      }
    });
  }
});