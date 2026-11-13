const $ = id => document.getElementById(id);
const api = window.API_BASE_URL.replace(/\/$/, '');
let token = sessionStorage.getItem('voice_agent_token');
let sessionId = null;
let mode = 'login';
let busy = false;
let historyOpen = false;
let historyLoadId = 0;

function status(message) { $('status').textContent = message; }
function addMessage(text, role) {
  const bubble = document.createElement('div');
  bubble.className = 'bubble ' + role;
  bubble.textContent = text;
  $('messages').appendChild(bubble);
  $('messages').scrollTop = $('messages').scrollHeight;
}
async function request(path, options={}) {
  const headers = {'Content-Type':'application/json', ...(token ? {'Authorization':'Bearer '+token}: {})};
  const response = await fetch(api + path, {...options, headers});
  const data = await response.json().catch(()=>({}));
  if (!response.ok) throw new Error(data.detail || 'Request failed');
  return data;
}
function setHistoryVisible(visible) {
  historyOpen = Boolean(visible && token);
  $('history-panel').classList.toggle('hidden', !historyOpen);
  $('toggle-history').setAttribute('aria-expanded', String(historyOpen));
}
function resetChat() {
  historyLoadId++;
  sessionId = null;
  $('messages').replaceChildren();
  addMessage('New interview started. What would you like to know?', 'assistant');
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  renderActiveSession();
}
function renderActiveSession() {
  document.querySelectorAll('.history-item').forEach(item => {
    item.classList.toggle('active', item.dataset.sessionId === sessionId);
  });
}
async function loadSessions() {
  if (!token) return;
  const list = $('history-list');
  try {
    const sessions = await request('/api/chat/sessions');
    list.replaceChildren();
    if (!sessions.length) {
      const empty = document.createElement('p');
      empty.className = 'history-empty';
      empty.textContent = 'No saved chats yet. Start a conversation!';
      list.appendChild(empty);
    }
    sessions.forEach(session => {
      const item = document.createElement('div');
      item.className = 'history-item';
      item.dataset.sessionId = session.session_id;
      const open = document.createElement('button');
      open.type = 'button';
      open.className = 'history-open';
      const title = document.createElement('span');
      title.className = 'history-title';
      title.textContent = session.title || 'Conversation';
      const date = document.createElement('span');
      date.className = 'history-date';
      date.textContent = new Date(session.updated_at).toLocaleString();
      open.append(title, date);
      open.onclick = () => openSession(session.session_id);
      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'history-delete';
      del.title = 'Delete conversation';
      del.setAttribute('aria-label', 'Delete ' + title.textContent);
      del.textContent = '×';
      del.onclick = () => deleteSession(session.session_id);
      item.append(open, del);
      list.appendChild(item);
    });
    renderActiveSession();
  } catch (error) {
    list.textContent = 'Could not load history: ' + error.message;
  }
}
async function openSession(id) {
  if (busy) { status('Wait for the current reply before switching chats'); return; }
  const loadId = ++historyLoadId;
  status('Loading conversation...');
  try {
    const messages = await request('/api/chat/sessions/' + encodeURIComponent(id));
    if (loadId !== historyLoadId) return;
    sessionId = id;
    $('messages').replaceChildren();
    messages.forEach(message => addMessage(message.content, message.role));
    renderActiveSession();
    status('Saved conversation loaded');
    if (window.matchMedia('(max-width:700px)').matches) setHistoryVisible(false);
  } catch (error) { status('Could not open conversation: ' + error.message); }
}
async function deleteSession(id) {
  if (busy) { status('Wait for the current reply before deleting a chat'); return; }
  if (!confirm('Permanently delete this conversation?')) return;
  try {
    await request('/api/chat/sessions/' + encodeURIComponent(id), {method: 'DELETE'});
    if (sessionId === id) resetChat();
    await loadSessions();
    status('Conversation deleted');
  } catch (error) { status('Could not delete conversation: ' + error.message); }
}
$('toggle-history').onclick = () => setHistoryVisible(!historyOpen);
$('close-history').onclick = () => setHistoryVisible(false);
$('history-new-chat').onclick = () => { if (busy) return; resetChat(); if (window.matchMedia('(max-width:700px)').matches) setHistoryVisible(false); };
function speak(text) {
  if (!$('speak').checked || !('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.02;
  utterance.lang = 'en-IN';
  speechSynthesis.speak(utterance);
}
async function send() {
  const message = $('message').value.trim();
  if (!message || busy) return;
  busy = true; $('send').disabled = true;
  $('message').value = ''; addMessage(message,'user'); status('Thinking...');
  try {
    const data = await request('/api/chat', {method:'POST', body:JSON.stringify({message,session_id:sessionId})});
    sessionId = data.session_id;
    addMessage(data.reply,'assistant'); speak(data.reply);
    status(data.saved ? 'Conversation saved' : 'Guest demo mode · history not saved');
    if (data.saved) loadSessions();
  } catch (error) { addMessage('Sorry, I could not answer just now. '+error.message,'assistant'); status('Connection error'); }
  finally { busy=false; $('send').disabled=false; $('message').focus(); }
}
$('send').addEventListener('click',send);
$('message').addEventListener('keydown',e=>{if(e.key==='Enter')send();});
$('new-chat').addEventListener('click',()=>{if (!busy) resetChat();});
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  const recognition = new SpeechRecognition();
  recognition.lang='en-IN'; recognition.interimResults=false;
  recognition.onstart=()=>{$('mic').classList.add('listening');status('Listening...');};
  recognition.onend=()=>{$('mic').classList.remove('listening');status('Ready');};
  recognition.onresult=e=>{$('message').value=e.results[0][0].transcript;send();};
  recognition.onerror=e=>status('Microphone error: '+e.error);
  $('mic').addEventListener('click',()=>recognition.start());
} else { $('mic').disabled=true; $('mic').title='Speech recognition not supported in this browser'; }
function showAuth(nextMode){mode=nextMode;$('auth-panel').classList.remove('hidden');$('auth-title').textContent=mode==='login'?'Sign in':'Create account';$('name-row').classList.toggle('hidden',mode==='login');$('name').required=mode==='register';$('auth-submit').textContent=mode==='login'?'Sign in':'Create account';}
$('show-login').onclick=()=>showAuth('login');
$('show-register').onclick=()=>showAuth('register');
$('close-auth').onclick=()=>$('auth-panel').classList.add('hidden');
$('google').onclick=()=>{window.location.href=api+'/api/auth/google/start';};
function signedIn(user) {
  $('auth-panel').classList.add('hidden');
  $('account').replaceChildren();
  const name = document.createElement('span');
  name.textContent = 'Hi, ' + user.name + ' ';
  const out = document.createElement('button');
  out.className = 'quiet';
  out.textContent = 'Sign out';
  out.onclick = () => { sessionStorage.removeItem('voice_agent_token'); location.reload(); };
  $('account').append(name, out);
  $('toggle-history').classList.remove('hidden');
  setHistoryVisible(true);
  status('Signed in · select a previous chat or start a new one');
  loadSessions();
}
$('auth-form').addEventListener('submit',async e=>{
 e.preventDefault();const payload={email:$('email').value,password:$('password').value};
 if(mode==='register')payload.name=$('name').value;
 try{const data=await request('/api/auth/'+(mode==='login'?'login':'register'),{method:'POST',body:JSON.stringify(payload)});token=data.token;sessionStorage.setItem('voice_agent_token',token);signedIn(data.user);}catch(err){alert(err.message);}
});
(async()=>{
 const match=location.hash.match(/^#oauth=([\w-]+)$/);
 if(match){history.replaceState(null,'',location.pathname);try{const data=await request('/api/auth/google/exchange',{method:'POST',body:JSON.stringify({code:match[1]})});token=data.token;sessionStorage.setItem('voice_agent_token',token);signedIn(data.user);}catch(e){status('Google sign-in failed: '+e.message);}return;}
 if(token){try{signedIn(await request('/api/auth/me'));}catch{sessionStorage.removeItem('voice_agent_token');token=null;}}
})();
