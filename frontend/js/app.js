const $ = id => document.getElementById(id);
const api = window.API_BASE_URL.replace(/\/$/, '');
let token = sessionStorage.getItem('voice_agent_token');
let sessionId = null;
let mode = 'login';
let busy = false;

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
  } catch (error) { addMessage('Sorry, I could not answer just now. '+error.message,'assistant'); status('Connection error'); }
  finally { busy=false; $('send').disabled=false; $('message').focus(); }
}
$('send').addEventListener('click',send);
$('message').addEventListener('keydown',e=>{if(e.key==='Enter')send();});
$('new-chat').addEventListener('click',()=>{sessionId=null; $('messages').replaceChildren(); addMessage('New interview started. What would you like to know?','assistant'); if('speechSynthesis' in window)speechSynthesis.cancel();});
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
function signedIn(user){$('auth-panel').classList.add('hidden');$('account').replaceChildren();const name=document.createElement('span');name.textContent='Hi, '+user.name+' ';const out=document.createElement('button');out.className='quiet';out.textContent='Sign out';out.onclick=()=>{sessionStorage.removeItem('voice_agent_token');location.reload();};$('account').append(name,out);status('Signed in · conversations saved');}
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
