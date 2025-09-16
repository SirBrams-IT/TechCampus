
/* ---------- Helper functions ---------- */
function getMentorData() {
  const el = document.getElementById("mentor-data");
  if (!el) return null;
  try { return JSON.parse(el.textContent); } catch(e) { console.error("mentor-data parse error", e); return null; }
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

/* ---------- Mentor Chat Class ---------- */
class MentorChat {
  constructor() {
    this.socket = null;
    this.currentConversation = null;
    this.conversationHistory = {}; // stores all chat history

    const mentorData = getMentorData();
    this.mentorId = mentorData?.id || null;

    // DOM elements
    this.conversationsContainer = document.getElementById('mentorConversations');
    this.chatMessages = document.getElementById('mentorChatMessages');
    this.messageInput = document.getElementById('mentorMessageInput');
    this.sendButton = document.getElementById('mentorSendButton');
    this.chatHeader = document.getElementById('mentorChatHeader');
    this.totalUnreadBadge = document.getElementById('totalUnreadBadge');

    if (this.sendButton) this.sendButton.addEventListener('click', () => this.sendMessage());
    if (this.messageInput) this.messageInput.addEventListener('keypress', e=>{if(e.key==='Enter') this.sendMessage();});

    if(this.mentorId) this.loadConversations();
  }

  async loadConversations() {
    if(!this.mentorId) return;
    try {
      const resp = await fetch(`/api/conversations/?user_type=mentor&user_id=${this.mentorId}`);
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

  refreshConversations(){ this.loadConversations(); }

  updateUnreadBadge(conversations){
    if(!this.totalUnreadBadge) return;
    const total = conversations.reduce((acc,c)=>acc+(c.unread_count||0),0);
    this.totalUnreadBadge.textContent = total>0?total:'';
  }

  renderConversations(conversations){
    if(!this.conversationsContainer) return;
    if(conversations.length===0){
      this.conversationsContainer.innerHTML = `<div class="text-center py-4 text-muted">No conversations yet</div>`;
      return;
    }
    let html='';
    conversations.forEach(c=>{
      const snippet = (c.last_message||'').substring(0,30)+((c.last_message||'').length>30?'...':'');
      const lastTime = c.last_message_time?new Date(c.last_message_time).toLocaleTimeString():'';
      const profile = c.profile_image || '/static/asset/img/profile.jpeg';
      html+=`
      <div class="conversation-item d-flex justify-content-between align-items-start py-2 px-2" data-id="${c.id}" style="cursor:pointer;">
        <div class="d-flex align-items-center flex-grow-1" onclick="window.mentorChat.selectConversation(${JSON.stringify(c).replace(/"/g,'&quot;')})">
          <img src="${profile}" class="rounded-circle me-2" style="width:30px;height:30px;object-fit:cover;">
          <div>
            <div class="fw-medium">${c.name}</div>
            <div class="small text-muted">${snippet}</div>
            <div class="small text-secondary">${lastTime}</div>
          </div>
        </div>
        <div class="d-flex align-items-center gap-1">
          ${c.unread_count>0?`<span class="badge bg-primary">${c.unread_count}</span>`:''}
          <button class="btn btn-sm btn-outline-danger" onclick="window.mentorChat.removeConversation(${c.id},event)">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>`;
    });
    this.conversationsContainer.innerHTML = html;
  }

  removeConversation(id,e){
    e.stopPropagation();
    const el = document.querySelector(`.conversation-item[data-id="${id}"]`);
    if(el) el.remove();
  }

  async selectConversation(conv){
    document.querySelectorAll('.conversation-item').forEach(el=>el.classList.remove('active'));
    const el = document.querySelector(`.conversation-item[data-id="${conv.id}"]`);
    if(el) el.classList.add('active');

    this.currentConversation = conv;
    this.chatHeader.innerHTML = `
      <h6 class="mb-0">
        <i class="bi bi-chat-left-text me-2"></i>${conv.name || 'Conversation'}
        ${conv.type==='forum'?'<span class="badge bg-info ms-2">Forum</span>':''}
      </h6>`;
    if(this.messageInput){this.messageInput.disabled=false; this.messageInput.focus();}
    if(this.sendButton) this.sendButton.disabled=false;

    this.connectToConversation(conv.id);
    await this.loadMessages(conv.id);
  }

  connectToConversation(convId){
    if(!this.mentorId) return console.error("mentorId missing");
    if(this.socket) try{this.socket.close();}catch(e){}
    const proto = window.location.protocol==='https:'?'wss':'ws';
    const url = `${proto}://${window.location.host}/ws/chat/${convId}/mentor/${this.mentorId}/`;
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
          is_own:d.is_own
        });
      }catch(err){console.error(err);}
    };
    this.socket.onerror = err=>console.error("WebSocket error",err);
    this.socket.onclose = ev=>console.warn("WebSocket closed",ev);
  }

  async loadMessages(convId){
    try{
      const resp = await fetch(`/api/messages/${convId}/?user_type=mentor&user_id=${this.mentorId}`);
      const data = await resp.json();
      if(data.error){ this.chatMessages.innerHTML=`<div class="text-center py-3 text-danger">Error loading messages</div>`; return; }

      this.chatMessages.innerHTML='';
      if(!data.messages || !data.messages.length){
        this.chatMessages.innerHTML = `<div class="text-center py-4 text-muted">
          <i class="bi bi-chat-left-text display-4"></i>
          <p class="mt-2">No messages yet</p>
          <p class="small">Start the conversation by sending a message</p>
        </div>`;
      }else{
        data.messages.forEach(msg=>{
          this.displayMessage({
            message: msg.content||msg.message||msg,
            sender_name: msg.sender_name,
            timestamp: msg.timestamp,
            is_own: !!msg.is_own
          });
        });
        this.chatMessages.scrollTop=this.chatMessages.scrollHeight;
      }
    }catch(err){
      console.error(err);
      this.chatMessages.innerHTML=`<div class="text-center py-3 text-danger">Failed to load messages</div>`;
    }
  }

  sendMessage(){
    if(!this.messageInput) return;
    const msg = this.messageInput.value.trim();
    if(!msg) return;
    if(this.socket && this.socket.readyState===WebSocket.OPEN){
      this.socket.send(JSON.stringify({message:msg,sender_type:'mentor',sender_id:this.mentorId}));
      this.messageInput.value='';
    }else{ alert('Connection error. Please try again.'); }
  }

  displayMessage(data){
    if(!this.chatMessages) return;
    if(this.chatMessages.querySelector('.text-muted')) this.chatMessages.innerHTML='';

    const div = document.createElement('div');
    div.className = `message mb-2 d-flex ${data.is_own?'justify-content-end':'justify-content-start'}`;
    div.innerHTML = `<div class="${data.is_own?'bg-primary text-white':'bg-light text-dark'} p-2 rounded" style="max-width:70%;">
      ${!data.is_own?`<div class="fw-semibold">${data.sender_name||''}</div>`:''}
      <div>${data.message}</div>
      <div class="small text-muted text-end">${data.timestamp?new Date(data.timestamp).toLocaleTimeString():''}</div>
    </div>`;
    this.chatMessages.appendChild(div);
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

    if(this.currentConversation){
      const cid = this.currentConversation.id;
      if(!this.conversationHistory[cid]) this.conversationHistory[cid]=[];
      this.conversationHistory[cid].push(data);
    }
  }
}

/* ---------- Student List + DM ---------- */
async function showStudentsList(){
  try{
    const resp = await fetch('/api/students/');
    const data = await resp.json();
    const list = document.getElementById('studentsList');
    if(!list) return;
    if(data.error){ list.innerHTML='<div class="text-center py-3 text-danger">Error loading students</div>'; return; }
    if(!data.students.length){ list.innerHTML='<div class="text-center py-3 text-muted">No students available</div>'; return; }

    let html='';
    data.students.forEach(s=>{
      html+=`<div class="student-item p-2 border-bottom d-flex align-items-center" style="cursor:pointer;" onclick="startDmWithStudent(${s.id})">
        <img src="${s.profile_image||'/static/asset/img/profile.jpeg'}" style="width:16px;height:16px;object-fit:cover;" class="rounded-circle me-2">
        <div>${s.name}</div>
      </div>`;
    });
    list.innerHTML = html;
    new bootstrap.Modal(document.getElementById('studentsModal')).show();
  }catch(err){ console.error(err); document.getElementById('studentsList').innerHTML='<div class="text-center py-3 text-danger">Failed to load students</div>'; }
}

function closeStudentsModal(){
  const modal = document.getElementById('studentsModal');
  const inst = bootstrap.Modal.getInstance(modal);
  if(inst) inst.hide();
}

async function startDmWithStudent(studentId){
  const mentorData = getMentorData();
  if(!mentorData?.id){ alert('Mentor not identified'); return; }
  const mentorId = mentorData.id;

  try{
    const resp = await fetch('/api/start_dm/',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},
      body:JSON.stringify({mentor_id:mentorId,student_id:studentId})
    });
    const data = await resp.json();
    if(data.error){ alert('Error starting conversation: '+data.error); return; }
    if(!data.conversation_id){ alert('No conversation created'); return; }

    closeStudentsModal();
    await window.mentorChat.loadConversations();
    try{
      const el = await waitForSelector(`.conversation-item[data-id="${data.conversation_id}"]`,3000);
      el.click();
    }catch{
      window.mentorChat.selectConversation({id:data.conversation_id,name:'Conversation'});
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
document.addEventListener('DOMContentLoaded',()=>{ window.mentorChat = new MentorChat(); });
