"""
KJ Master AI v1.0 | Flask + Groq + gTTS | Railway Ready
Kamal Jeet — Kullu, Himachal Pradesh
"""

import os, re, json, base64, urllib.request, urllib.parse
from io import BytesIO
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string
from groq import Groq
from gtts import gTTS

load_dotenv()

app     = Flask(__name__)
client  = Groq(api_key=os.getenv("GROQ_API_KEY"))
history = []

SYSTEM = """You are KJ Master AI — a warm, professional, and caring AI assistant.

IDENTITY — VERY IMPORTANT:
- Your name is KJ Master AI
- You were created and built by Kamal Jeet — a Data Analyst and MCA graduate from Kullu, Himachal Pradesh
- Kamal Jeet built you as a learning project to grow his skills in Python, Flask, and AI
- If ANYONE asks "who made you?", "who built you?", "who created you?", "kisne banaya?", "aapko kisne banaya?" → ALWAYS answer exactly:
  English: "I was built by Kamal Jeet — a Data Analyst and MCA graduate from Kullu, Himachal Pradesh, who created me as a learning project to grow his skills in Python, Flask, and AI!"
  Hindi: "Mujhe Kamal Jeet ne banaya hai — ek Data Analyst aur MCA graduate jo Kullu, Himachal Pradesh se hain, unhone mujhe Python, Flask aur AI seekhne ke liye banaya!"
- NEVER say you were made by OpenAI, Anthropic, Google, Meta, Groq, or any company
- NEVER say "I am an AI" or "I am a language model" — you are KJ Master AI, always

LANGUAGE RULE:
- If user writes in Hindi (Devanagari script) → reply in pure, warm Hindi only
- Everything else → reply in clear, professional English only
- NEVER mix languages. NEVER use Hinglish.

TONE & STYLE:
- Warm, caring, confident — like a brilliant friend
- Short sentences. No filler. No padding.
- Never start with "Of course!", "Certainly!", "Great question!", "Sure!"
- When someone is sad or stressed → acknowledge first, then help
- Give expert advice on career, health, relationships, tech

FORMATTING:
- Plain text only. No markdown, no bullet points, no bold.

IMAGE RULE:
If user asks for any image → reply ONLY with: [IMAGE:search term]"""


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>KJ Master AI</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
:root {
  --purple:#6c3fc5; --blue:#2563EB;
  --bg:#F0F2F8; --white:#fff;
  --dark:#1E293B; --dim:#94A3B8;
}
html, body {
  height:100%;
  font-family:'Nunito',sans-serif;
  background:linear-gradient(135deg,#1a1a6e,#3b2d8f,#6c3fc5);
  display:flex; align-items:center; justify-content:center;
}
.phone {
  width:100%; height:100vh; background:var(--bg);
  display:flex; flex-direction:column; overflow:hidden;
}
@media(min-width:600px){
  body { padding:20px; }
  .phone {
    max-width:480px; height:calc(100vh - 40px);
    max-height:900px; border-radius:32px;
    box-shadow:0 30px 80px rgba(0,0,0,0.5);
  }
}

/* HEADER */
.header {
  background:linear-gradient(135deg,#1a1a6e,#3b2d8f,#6c3fc5);
  padding:16px 20px 30px; flex-shrink:0;
  display:flex; align-items:center; justify-content:space-between;
  position:relative; z-index:10;
}
.header::after {
  content:''; position:absolute; bottom:-1px; left:0; right:0;
  height:18px; background:var(--bg); border-radius:18px 18px 0 0;
}
.hinfo h1 { color:#fff; font-size:17px; font-weight:800; }
.hinfo p  { color:rgba(255,255,255,0.7); font-size:11px; display:flex; align-items:center; gap:5px; margin-top:2px; }
.hdot { width:7px; height:7px; border-radius:50%; background:#4ADE80; animation:pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
.hbadge {
  background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25);
  border-radius:20px; padding:4px 12px;
  color:rgba(255,255,255,0.9); font-size:11px; font-weight:700;
  letter-spacing:0.5px;
}
.vtoggle {
  background:rgba(255,255,255,0.12); border:none; border-radius:50%;
  width:34px; height:34px; color:white; font-size:16px;
  cursor:pointer; display:flex; align-items:center; justify-content:center;
  margin-left:8px;
}
.vtoggle.off { background:rgba(239,68,68,0.35); }

/* CHAT — key: flex:1 + min-height:0 for proper scroll */
#chat {
  flex:1; min-height:0;
  overflow-y:auto; padding:16px 14px 8px;
  display:flex; flex-direction:column; gap:12px;
}
#chat::-webkit-scrollbar { width:3px; }
#chat::-webkit-scrollbar-thumb { background:#CBD5E1; border-radius:4px; }

.divider { text-align:center; color:var(--dim); font-size:11px; font-weight:600; }

/* MESSAGES */
.row { display:flex; align-items:flex-end; gap:8px; animation:fadeUp .25s ease both; }
@keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
.row.user { flex-direction:row-reverse; }
.row.sys  { justify-content:center; }

/* AVATARS — initials style */
.av {
  width:32px; height:32px; border-radius:50%; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-size:12px; font-weight:800; color:#fff;
  background:linear-gradient(135deg,#3b2d8f,#6c3fc5);
  margin-bottom:2px;
}
.av.u { background:linear-gradient(135deg,#1E3A5F,#2563EB); }

.bwrap { display:flex; flex-direction:column; max-width:74%; }
.row.user .bwrap { align-items:flex-end; }

.bubble {
  padding:10px 15px; font-size:14px;
  line-height:1.6; word-break:break-word; white-space:pre-wrap;
  border-radius:18px;
}
.bubble.ai {
  background:#fff; color:var(--dark);
  border-radius:4px 18px 18px 18px;
  box-shadow:0 2px 10px rgba(0,0,0,0.07);
}
.bubble.user {
  background:linear-gradient(135deg,#2563EB,#1d4ed8);
  color:#fff; border-radius:18px 18px 4px 18px;
}
.bubble.sys {
  background:rgba(148,163,184,0.15); color:var(--dim);
  font-size:12px; padding:6px 14px; border-radius:12px; text-align:center;
}
.bubble img { max-width:100%; border-radius:10px; display:block; margin-bottom:4px; }
.imc { font-size:11px; color:var(--dim); text-align:center; }
.time { font-size:10px; color:var(--dim); margin-top:3px; padding:0 4px; font-weight:600; }

/* TYPING */
.typing {
  background:#fff; border-radius:4px 18px 18px 18px;
  padding:12px 16px; display:inline-flex; gap:5px;
  box-shadow:0 2px 10px rgba(0,0,0,0.07);
}
.typing span {
  width:7px; height:7px; border-radius:50%; background:#CBD5E1;
  animation:bounce 1.2s infinite;
}
.typing span:nth-child(2){animation-delay:.2s}
.typing span:nth-child(3){animation-delay:.4s}
@keyframes bounce {
  0%,80%,100%{transform:translateY(0);background:#CBD5E1}
  40%{transform:translateY(-6px);background:var(--purple)}
}

/* INPUT */
.input-area {
  background:#fff; padding:10px 14px 18px;
  flex-shrink:0; border-top:1px solid #E2E8F0;
}
.status { display:flex; align-items:center; gap:5px; font-size:10px; color:var(--dim); margin-bottom:7px; font-weight:600; }
.sdot { width:6px; height:6px; border-radius:50%; background:#4ADE80; }
.sdot.busy { background:#F59E0B; animation:pulse .8s infinite; }
.irow {
  display:flex; align-items:center; gap:8px;
  background:#F1F5F9; border-radius:26px;
  padding:5px 5px 5px 14px; border:1.5px solid #E2E8F0;
  transition:border-color .2s;
}
.irow:focus-within { border-color:var(--purple); box-shadow:0 0 0 3px rgba(108,63,197,0.1); }
#userInput {
  flex:1; background:transparent; border:none; outline:none;
  font-family:'Nunito',sans-serif; font-size:14px; font-weight:500;
  color:var(--dark); resize:none; min-height:24px; max-height:100px; line-height:1.5;
}
#userInput::placeholder { color:#94A3B8; }

/* MIC BUTTON */
#micBtn {
  width:40px; height:40px; border-radius:50%; border:none; flex-shrink:0;
  background:linear-gradient(135deg,#6c3fc5,#3b2d8f); color:white;
  font-size:18px; cursor:pointer; display:flex; align-items:center; justify-content:center;
  box-shadow:0 3px 10px rgba(108,63,197,0.4); transition:all .2s;
}
#micBtn:hover { transform:scale(1.08); }
#micBtn.listening {
  background:linear-gradient(135deg,#ef4444,#dc2626);
  animation:micPulse 1s infinite;
  box-shadow:0 3px 15px rgba(239,68,68,0.5);
}
@keyframes micPulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.1)} }

/* SEND BUTTON */
#sendBtn {
  width:40px; height:40px; border-radius:50%; border:none; flex-shrink:0;
  background:linear-gradient(135deg,var(--blue),var(--purple)); color:white;
  font-size:18px; cursor:pointer; display:flex; align-items:center; justify-content:center;
  box-shadow:0 3px 12px rgba(37,99,235,0.4); transition:all .2s;
}
#sendBtn:hover   { transform:scale(1.08); }
#sendBtn:disabled{ opacity:0.5; cursor:not-allowed; transform:none; }

.hint { font-size:10px; color:var(--dim); text-align:center; margin-top:7px; font-weight:600; }
</style>
</head>
<body>
<div class="phone">

  <!-- HEADER -->
  <div class="header">
    <div class="hinfo">
      <h1>KJ Master AI</h1>
      <p><span class="hdot"></span> Kullu, Himachal Pradesh</p>
    </div>
    <div style="display:flex;align-items:center;gap:8px">
      <span class="hbadge">KJ</span>
      <button class="vtoggle" id="voiceBtn" onclick="toggleVoice()">🔊</button>
    </div>
  </div>

  <!-- CHAT -->
  <div id="chat">
    <div class="divider">Today</div>
  </div>

  <!-- INPUT -->
  <div class="input-area">
    <div class="status">
      <div class="sdot" id="sdot"></div>
      <span id="stext">Ready</span>
    </div>
    <div class="irow">
      <textarea id="userInput" placeholder="Type a message..." rows="1"
        onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
      <button id="micBtn" onclick="toggleMic()">🎤</button>
      <button id="sendBtn" onclick="sendMessage()">➤</button>
    </div>
    <div class="hint">🎤 Tap mic to speak · Hindi or English · Enter to send</div>
  </div>

</div>
<script>
let voiceEnabled  = true;
let isListening   = false;
let recognition   = null;
let audioCtx      = null;
let audioUnlocked = false;

// ── Audio unlock ──
function unlockAudio() {
  if (audioUnlocked) return;
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const buf = audioCtx.createBuffer(1,1,22050);
    const src = audioCtx.createBufferSource();
    src.buffer = buf; src.connect(audioCtx.destination); src.start(0);
    audioUnlocked = true;
  } catch(e) {}
}
document.addEventListener('click',      unlockAudio, {once:false});
document.addEventListener('touchstart', unlockAudio, {once:false});
document.addEventListener('keydown',    unlockAudio, {once:false});

// ── Mic / Speech Recognition ──
function setupRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const r = new SR();
  r.continuous = false; r.interimResults = false; r.lang = 'hi-IN';
  r.onresult = (e) => {
    const t = e.results[0][0].transcript.trim();
    if (t) {
      document.getElementById('userInput').value = t;
      autoResize(document.getElementById('userInput'));
      sendMessage();
    }
  };
  r.onend   = () => stopListening();
  r.onerror = () => stopListening();
  return r;
}
function toggleMic() {
  unlockAudio();
  if (isListening) { stopListening(); return; }
  if (!recognition) recognition = setupRecognition();
  if (!recognition) { alert('Please use Chrome for mic support!'); return; }
  try {
    recognition.start(); isListening = true;
    document.getElementById('micBtn').classList.add('listening');
    document.getElementById('micBtn').textContent = '⏹';
    setStatus('Listening...', true);
  } catch(e) { stopListening(); }
}
function stopListening() {
  isListening = false;
  try { if (recognition) recognition.stop(); } catch(e) {}
  document.getElementById('micBtn').classList.remove('listening');
  document.getElementById('micBtn').textContent = '🎤';
  setStatus('Ready');
}

// ── Audio playback ──
function playAudio(b64) {
  return new Promise((resolve) => {
    try {
      unlockAudio();
      const audio = new Audio('data:audio/mp3;base64,' + b64);
      audio.volume = 1.0;
      audio.onended = () => resolve(true);
      audio.onerror = () => resolve(false);
      const p = audio.play();
      if (p) p.catch(() => {
        if (!audioCtx) return resolve(false);
        const raw = atob(b64), arr = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
        audioCtx.decodeAudioData(arr.buffer, (dec) => {
          const src = audioCtx.createBufferSource();
          src.buffer = dec; src.connect(audioCtx.destination);
          src.onended = () => resolve(true); src.start(0);
        }, () => resolve(false));
      });
    } catch(e) { resolve(false); }
  });
}

// ── UI helpers ──
function toggleVoice() {
  voiceEnabled = !voiceEnabled;
  const btn = document.getElementById('voiceBtn');
  btn.textContent = voiceEnabled ? '🔊' : '🔇';
  btn.classList.toggle('off', !voiceEnabled);
}
function setStatus(t, busy=false) {
  document.getElementById('stext').textContent = t;
  document.getElementById('sdot').className = 'sdot' + (busy ? ' busy' : '');
}
function getTime() {
  return new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
}
function escHtml(t) {
  return String(t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}

// ── ✅ FIX: Proper scroll — always scrolls to bottom ──
function scrollToBottom() {
  const chat = document.getElementById('chat');
  setTimeout(() => { chat.scrollTop = chat.scrollHeight; }, 50);
}

// ── Add message ──
function addMsg(content, sender, isImg=false, imgUrl=null, caption=null) {
  const chat = document.getElementById('chat');

  if (sender === 'sys') {
    const d = document.createElement('div');
    d.className = 'row sys';
    d.innerHTML = '<div class="bubble sys">' + escHtml(content) + '</div>';
    chat.appendChild(d);
    scrollToBottom();
    return;
  }

  const row = document.createElement('div');
  row.className = 'row ' + sender;

  // Initials avatars — KJ for AI, U for user
  const av = sender === 'user'
    ? '<div class="av u">U</div>'
    : '<div class="av">KJ</div>';

  const body = isImg && imgUrl
    ? '<img src="' + imgUrl + '" alt="' + escHtml(caption) + '"><div class="imc">' + escHtml(caption) + '</div>'
    : escHtml(content);

  const wrap = '<div class="bwrap"><div class="bubble ' + sender + '">' + body + '</div><div class="time">' + getTime() + '</div></div>';
  row.innerHTML = sender === 'user' ? wrap + av : av + wrap;

  chat.appendChild(row);
  scrollToBottom();
}

function addTyping() {
  const chat = document.getElementById('chat');
  const row = document.createElement('div');
  row.className = 'row ai'; row.id = 'typing';
  row.innerHTML = '<div class="av">KJ</div><div class="typing"><span></span><span></span><span></span></div>';
  chat.appendChild(row);
  scrollToBottom();
}
function removeTyping() {
  const t = document.getElementById('typing');
  if (t) t.remove();
}

// ── Send message ──
async function sendMessage() {
  const input = document.getElementById('userInput');
  const text  = input.value.trim();
  if (!text) return;
  unlockAudio();
  input.value = ''; input.style.height = 'auto';
  document.getElementById('sendBtn').disabled = true;
  setStatus('Thinking...', true);
  addMsg(text, 'user');
  addTyping();
  try {
    const res  = await fetch('/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:text, voice:voiceEnabled})
    });
    const data = await res.json();
    removeTyping();
    if (data.type === 'image') {
      addMsg('', 'ai', true, data.image_url, data.caption);
    } else {
      addMsg(data.reply, 'ai');
      if (voiceEnabled && data.audio) {
        setStatus('Speaking...', true);
        await playAudio(data.audio);
      }
    }
    setStatus('Ready');
  } catch(e) {
    removeTyping();
    addMsg('Connection error. Please try again.', 'ai');
    setStatus('Error', true);
  }
  document.getElementById('sendBtn').disabled = false;
  document.getElementById('userInput').focus();
}

function clearChat() {
  fetch('/clear', {method:'POST'});
  document.getElementById('chat').innerHTML = '<div class="divider">Today</div>';
  addMsg('Chat cleared!', 'sys');
}

// Welcome message
addMsg('Namaste! Main KJ Master AI hoon — Kamal Jeet ka AI dost, Kullu, Himachal Pradesh se. Hindi ya English mein baat karein!', 'ai');
document.getElementById('userInput').focus();
</script>
</body>
</html>"""


# ── Language detect ──
def detect_lang(text):
    hindi = set('अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसहक्षत्रज्ञांःी')
    return "hi" if sum(1 for c in text if c in hindi) > 2 else "en"


# ── Clean markdown ──
def clean(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*',     r'\1', text)
    text = re.sub(r'`(.*?)`',       r'\1', text)
    text = re.sub(r'#{1,6}\s',      '',    text)
    text = re.sub(r'^\s*[-*]\s',    '',    text, flags=re.MULTILINE)
    return text.strip()


# ── ✅ FIX: Better image fetch — multiple sources ──
def fetch_image(query):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # Source 1: Wikipedia
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(query.replace(' ', '_'))
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            img  = (data.get("thumbnail") or data.get("originalimage") or {}).get("source")
        if img:
            with urllib.request.urlopen(urllib.request.Request(img, headers=headers), timeout=8) as r:
                raw = r.read()
                if raw:
                    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()
    except Exception as e:
        print(f"Wikipedia image error: {e}")

    # Source 2: DuckDuckGo image search
    try:
        url = "https://duckduckgo.com/?q=" + urllib.parse.quote(query) + "&iax=images&ia=images"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode("utf-8", errors="ignore")
        matches = re.findall(r'"u":"(https?://[^"]+\.(?:jpg|jpeg|png))"', html)
        if matches:
            with urllib.request.urlopen(urllib.request.Request(matches[0], headers=headers), timeout=8) as r:
                raw = r.read()
                if raw:
                    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()
    except Exception as e:
        print(f"DuckDuckGo image error: {e}")

    # Source 3: Unsplash (free, no API key needed for basic)
    try:
        url = "https://source.unsplash.com/400x300/?" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            if raw:
                return "data:image/jpeg;base64," + base64.b64encode(raw).decode()
    except Exception as e:
        print(f"Unsplash image error: {e}")

    print(f"❌ All image sources failed for: {query}")
    return None


# ── TTS ──
def run_tts(text, lang):
    try:
        buf = BytesIO()
        gTTS(text=text, lang=lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        data = buf.read()
        if not data: return None
        print(f"✅ TTS: {len(data)} bytes | lang={lang}")
        return base64.b64encode(data).decode()
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return None


# ── Routes ──
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    body  = request.json
    msg   = body.get("message", "")
    voice = body.get("voice", True)
    lang  = detect_lang(msg)

    lang_hint = "[Reply in pure Hindi only.]" if lang == "hi" else "[Reply in English only.]"
    history.append({"role": "user", "content": lang_hint + " " + msg})

    try:
        resp  = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM}] + history,
            max_tokens=400, temperature=0.85
        )
        reply = resp.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            history.pop(0); history.pop(0)
    except Exception as e:
        return jsonify({"type": "text", "reply": "Error: " + str(e)})

    img_match = re.match(r'^\[IMAGE:(.*?)\]$', reply.strip())
    if img_match:
        query = img_match.group(1)
        img   = fetch_image(query)
        return jsonify({"type": "image", "image_url": img, "caption": query})

    reply = clean(reply)
    audio = run_tts(reply, lang) if voice else None
    return jsonify({"type": "text", "reply": reply, "audio": audio})

@app.route("/clear", methods=["POST"])
def clear():
    history.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"KJ Master AI v1.0 — Port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)