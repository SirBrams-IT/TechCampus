/* ---------- Helper functions ---------- */
function getStudentData() {
  const el = document.getElementById("student-data");
  if (!el) return null;
  try { return JSON.parse(el.textContent); } catch(e) { console.error("student-data parse error", e); return null; }
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

function waitForSelector(selector, timeout=4000){
  return new Promise((resolve,reject)=>{
    const el = document.querySelector(selector);
    if(el) return resolve(el);
    const obs = new MutationObserver(()=>{
      const found = document.querySelector(selector);
      if(found){ obs.disconnect(); clearTimeout(timer); resolve(found);}
    });
    obs.observe(document.body,{childList:true,subtree:true});
    const timer = setTimeout(()=>{obs.disconnect(); reject("timeout "+selector)},timeout);
  });
}

/* ---------- Student Chat Class ---------- */
class StudentChat {
  constructor() {
    this.socket = null;
    this.currentConversation = null;
    this.conversationHistory = {};
    this.page = {};

    const studentData = getStudentData();
    this.studentId = studentData?.id || null;

    // DOM elements
    this.conversationsContainer = document.getElementById('studentConversations');
    this.chatMessages = document.getElementById('studentChatMessages');
    this.messageInput = document.getElementById('studentMessageInput');
    this.sendButton = document.getElementById('studentSendButton');
    this.chatHeader = document.getElementById('studentChatHeader');
    this.totalUnreadBadge = document.getElementById('totalUnreadBadge');

    if (this.sendButton) this.sendButton.addEventListener('click', () => this.sendMessage());
    if (this.messageInput) this.messageInput.addEventListener('keypress', e=>{if(e.key==='Enter') this.sendMessage();});

    // infinite scroll
    if (this.chatMessages) {
      this.chatMessages.addEventListener('scroll', () => {
        if (this.chatMessages.scrollTop === 0) {
          this.loadOlderMessages();
        }
      });
    }

    if(this.studentId) this.loadConversations();
  }

  async loadConversations() {
    if(!this.studentId) return;
    try {
      const resp = await fetch(`/api/conversations/?user_type=student&user_id=${this.studentId}`);
      const data = await resp.json();
      if(data.error){
        this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Error loading conversations</div>`;
        return;
      }
      this.renderConversations(data.conversations || []);
      this.updateUnreadBadge(data.conversations || []);
    }catch(err){
      console.error(err);
      this.conversationsContainer.innerHTML = `<div class="text-center py-3 text-danger">Failed to load conversations</div>`;
    }
  }

  updateUnreadBadge(conversations){
    if(!this.totalUnreadBadge) return;
    const total = conversations.reduce((acc,c)=>acc+(c.unread_count||0),0);
    this.totalUnreadBadge.textContent = total>0?total:'';
  }

  renderConversations(conversations){
    if(!this.conversationsContainer) return;
    if(conversations.length===0){
      this.conversationsContainer.innerHTML = `
        <div class="text-center py-4 text-muted">
          <i class="bi bi-chat-left-text display-4"></i>
          <p class="mt-2">No conversations yet</p>
          <button onclick="showMentorsList()" class="btn btn-sm btn-primary mt-2">
            Message a mentor
          </button>
        </div>`;
      return;
    }
    let html='';
    conversations.forEach(c=>{
      const snippet = (c.last_message||'').substring(0,30)+((c.last_message||'').length>30?'...':'');
      const lastTime = c.last_message_time?new Date(c.last_message_time).toLocaleTimeString():'';
      const profile = c.profile_image || '/static/asset/img/profile.jpeg';
      html+=`
      <div class="conversation-item d-flex justify-content-between align-items-start py-2 px-2" data-id="${c.id}" style="cursor:pointer;">
        <div class="d-flex align-items-center flex-grow-1" onclick="window.studentChat.selectConversation(${JSON.stringify(c).replace(/"/g,'&quot;')})">
          <img src="${profile}" class="rounded-circle me-2" style="width:30px;height:30px;object-fit:cover;">
          <div>
            <div class="fw-medium">${c.name}</div>
            <div class="small text-muted">${snippet}</div>
            <div class="small text-secondary">${lastTime}</div>
          </div>
        </div>
        ${c.unread_count>0?`<span class="badge bg-primary">${c.unread_count}</span>`:''}
      </div>`;
    });
    this.conversationsContainer.innerHTML = html;
  }

  async selectConversation(conv){
    document.querySelectorAll('.conversation-item').forEach(el=>el.classList.remove('active'));
    const el = document.querySelector(`.conversation-item[data-id="${conv.id}"]`);
    if(el) el.classList.add('active');

    this.currentConversation = conv;
    this.page[conv.id] = 1;
    this.chatHeader.innerHTML = `
      <h6 class="mb-0">
        <i class="bi bi-chat-left-text me-2"></i>${conv.name || 'Conversation'}
        ${conv.type==='forum'?'<span class="badge bg-info ms-2">Forum</span>':''}
      </h6>`;
    if(this.messageInput){this.messageInput.disabled=false; this.messageInput.focus();}
    if(this.sendButton) this.sendButton.disabled=false;

    this.connectToConversation(conv.id);
    await this.loadMessages(conv.id, 1);
  }

  connectToConversation(convId){
    if(!this.studentId) return console.error("studentId missing");
    if(this.socket) try{this.socket.close();}catch(e){}
    const proto = window.location.protocol==='https:'?'wss':'ws';
    const url = `${proto}://${window.location.host}/ws/chat/${convId}/student/${this.studentId}/`;
    console.log("Connecting WS:",url);

    this.socket = new WebSocket(url);
    this.socket.onopen = ()=>console.log("WebSocket opened");
    this.socket.onmessage = e=>{
      try{
        const d=JSON.parse(e.data);
        this.displayMessage({
          message:d.message,
          sender_name:d.sender_name,
          timestamp:d.timestamp,
          is_own:d.is_own,
          status:d.status||"sent"
        }, "append");
      }catch(err){console.error(err);}
    };
    this.socket.onerror = err=>console.error("WebSocket error",err);
    this.socket.onclose = ev=>console.warn("WebSocket closed",ev);
  }

  async loadMessages(convId, page=1){
    try{
      if(page===1){
        this.chatMessages.innerHTML = `<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div> Loading...</div>`;
      }

      const resp = await fetch(`/api/messages/${convId}/?user_type=student&user_id=${this.studentId}&page=${page}`);
      const data = await resp.json();
      if(data.error){ this.chatMessages.innerHTML=`<div class="text-center py-3 text-danger">Error loading messages</div>`; return; }

      if(page===1 && !this.conversationHistory[convId]) this.chatMessages.innerHTML='';

      if(!data.messages || !data.messages.length){
        if(page===1){
          this.chatMessages.innerHTML = `<div class="text-center py-4 text-muted">
            <i class="bi bi-chat-left-text display-4"></i>
            <p class="mt-2">No messages yet</p>
            <p class="small">Start the conversation by sending a message</p>
          </div>`;
        }
      }else{
        data.messages.forEach(msg=>{
          this.displayMessage({
            message: msg.content||msg.message||msg,
            sender_name: msg.sender_name,
            timestamp: msg.timestamp,
            is_own: !!msg.is_own,
            status: msg.status || "delivered"
          }, page===1 ? "append" : "prepend");
        });
        if(page===1) this.chatMessages.scrollTop=this.chatMessages.scrollHeight;
      }
    }catch(err){
      console.error(err);
      this.chatMessages.innerHTML=`<div class="text-center py-3 text-danger">Failed to load messages</div>`;
    }
  }

  async loadOlderMessages(){
    if(!this.currentConversation) return;
    const convId = this.currentConversation.id;
    this.page[convId] = (this.page[convId]||1) + 1;
    const oldHeight = this.chatMessages.scrollHeight;
    await this.loadMessages(convId, this.page[convId]);
    const newHeight = this.chatMessages.scrollHeight;
    this.chatMessages.scrollTop = newHeight - oldHeight;
  }

  sendMessage(){
    if(!this.messageInput) return;
    const msg = this.messageInput.value.trim();
    if(!msg) return;
    if(this.socket && this.socket.readyState===WebSocket.OPEN){
      const payload = {message:msg,sender_type:'student',sender_id:this.studentId,status:"sent"};
      this.socket.send(JSON.stringify(payload));
      this.messageInput.value='';
    }else{ alert('Connection error. Please try again.'); }
  }

  displayMessage(data, mode="append"){
    if(!this.chatMessages) return;

    const exists = Array.from(this.chatMessages.querySelectorAll('.message')).some(el=>{
      return el.dataset.timestamp === data.timestamp && el.dataset.sender === data.sender_name;
    });
    if(exists) {
      const existing = this.chatMessages.querySelector(`.message[data-timestamp="${data.timestamp}"][data-sender="${data.sender_name}"]`);
      if(existing){
        const statusEl = existing.querySelector('.msg-status');
        if(statusEl) statusEl.innerHTML = this.getStatusIcon(data.status, data.is_own);
      }
      return;
    }

    const div = document.createElement('div');
    div.className = `message mb-2 d-flex ${data.is_own?'justify-content-end':'justify-content-start'}`;
    div.dataset.timestamp = data.timestamp;
    div.dataset.sender = data.sender_name;

    const statusIcon = this.getStatusIcon(data.status, data.is_own);

    div.innerHTML = `<div class="${data.is_own?'bg-primary text-white':'bg-light text-dark'} p-2 rounded shadow-sm" style="max-width:70%;">
      <div>${data.message}</div>
      <div class="small text-muted text-end">
        ${data.timestamp?new Date(data.timestamp).toLocaleTimeString():''} 
        <span class="msg-status">${statusIcon}</span>
      </div>
    </div>`;

    if(mode==="prepend"){
      this.chatMessages.insertBefore(div,this.chatMessages.firstChild);
    }else{
      this.chatMessages.appendChild(div);
      this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    if(this.currentConversation){
      const cid = this.currentConversation.id;
      if(!this.conversationHistory[cid]) this.conversationHistory[cid]=[];
      this.conversationHistory[cid].push(data);
    }
  }

  getStatusIcon(status, isOwn){
    if(!isOwn) return "";
    if(status==="sent") return `<i class="bi bi-check"></i>`;
    if(status==="delivered") return `<i class="bi bi-check2-all"></i>`;
    if(status==="read") return `<i class="bi bi-check2-all text-primary"></i>`;
    return "";
  }
}

/* ---------- Mentor List + DM ---------- */
async function showMentorsList(){
  try{
    const resp = await fetch('/api/mentors/');
    const data = await resp.json();
    const list = document.getElementById('mentorsList');
    if(!list) return;
    if(data.error){ list.innerHTML='<div class="text-center py-3 text-danger">Error loading mentors</div>'; return; }
    if(!data.mentors.length){ list.innerHTML='<div class="text-center py-3 text-muted">No mentors available</div>'; return; }

    let html='';
    data.mentors.forEach(m=>{
      html+=`<div class="mentor-item p-2 border-bottom d-flex align-items-center" style="cursor:pointer;" onclick="startDmWithMentor(${m.id})">
        <img src="${m.profile_image||'/static/asset/img/profile.jpeg'}" style="width:16px;height:16px;object-fit:cover;" class="rounded-circle me-2">
        <div>${m.name}</div>
      </div>`;
    });
    list.innerHTML = html;
    new bootstrap.Modal(document.getElementById('mentorsModal')).show();
  }catch(err){ console.error(err); document.getElementById('mentorsList').innerHTML='<div class="text-center py-3 text-danger">Failed to load mentors</div>'; }
}

function closeMentorsModal(){
  const modal = document.getElementById('mentorsModal');
  const inst = bootstrap.Modal.getInstance(modal);
  if(inst) inst.hide();
}

async function startDmWithMentor(mentorId){
  const studentData = getStudentData();
  if(!studentData?.id){ alert('Student not identified'); return; }
  const studentId = studentData.id;

  try{
    const resp = await fetch('/api/start_dm/',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},
      body:JSON.stringify({student_id:studentId,mentor_id:mentorId})
    });
    const data = await resp.json();
    if(data.error){ alert('Error starting conversation: '+data.error); return; }
    if(!data.conversation_id){ alert('No conversation created'); return; }

    closeMentorsModal();
    await window.studentChat.loadConversations();
    try{
      const el = await waitForSelector(`.conversation-item[data-id="${data.conversation_id}"]`,3000);
      el.click();
    }catch{
      window.studentChat.selectConversation({id:data.conversation_id,name:'Conversation'});
    }
  }catch(err){ console.error(err); alert('Failed to start conversation'); }
}

/* ---------- Filter Conversations ---------- */
function filterConversations(search){
  const items = document.querySelectorAll('.conversation-item');
  search = (search||'').toLowerCase();
  items.forEach(i=>{ i.style.display=(i.textContent||'').toLowerCase().includes(search)?'flex':'none'; });
}

/* ---------- Initialize ---------- */
document.addEventListener('DOMContentLoaded',()=>{ window.studentChat = new StudentChat(); });
