import os
import base64
import asyncio
import urllib.request
import urllib.parse
import re

from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv
from groq import Groq
import edge_tts

load_dotenv()

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

history = []

SYSTEM = """
You are KJ Master AI - a friendly, smart AI assistant.

You understand Hindi, English and Hinglish fluently.
Always reply in the same language the user speaks.
Keep replies short and natural for voice conversation.

If user asks to show/dikhao any image or picture, reply EXACTLY like this:
[IMAGE:object]

Example:
User: show me a lion
Reply: [IMAGE:lion]

User: tiger dikhao
Reply: [IMAGE:tiger]
"""

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KJ Master AI</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #0f172a;
  color: white;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

header {
  background: linear-gradient(135deg, #1e293b, #334155);
  padding: 16px;
  text-align: center;
  font-size: 22px;
  font-weight: bold;
  letter-spacing: 1px;
  border-bottom: 1px solid #475569;
}

#status {
  text-align: center;
  padding: 6px;
  font-size: 13px;
  color: #94a3b8;
  background: #1e293b;
  min-height: 28px;
}

#chat {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.msg {
  padding: 10px 14px;
  border-radius: 14px;
  max-width: 75%;
  line-height: 1.5;
  font-size: 15px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.user {
  background: #2563eb;
  align-self: flex-end;
  border-bottom-right-radius: 4px;
}

.ai {
  background: #334155;
  align-self: flex-start;
  border-bottom-left-radius: 4px;
}

.img-msg {
  align-self: flex-start;
}

.img-msg img {
  max-width: 260px;
  border-radius: 12px;
  border: 2px solid #475569;
}

#input {
  display: flex;
  padding: 12px;
  background: #1e293b;
  gap: 8px;
  border-top: 1px solid #334155;
}

#text {
  flex: 1;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #475569;
  background: #0f172a;
  color: white;
  font-size: 15px;
  outline: none;
}

#text:focus { border-color: #6366f1; }

button {
  padding: 10px 16px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  transition: all 0.2s;
}

#sendBtn {
  background: #6366f1;
  color: white;
}

#sendBtn:hover { background: #4f46e5; }

#micBtn {
  background: #334155;
  color: white;
  min-width: 48px;
}

#micBtn.listening {
  background: #dc2626;
  animation: pulse 1s infinite;
}

#talkBtn {
  background: #059669;
  color: white;
}

#talkBtn.active {
  background: #dc2626;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.6; }
}
</style>
</head>
<body>

<header>🤖 KJ Master AI</header>
<div id="status">Ready — Type or press 🎤 to speak</div>

<div id="chat"></div>

<div id="input">
  <input id="text" placeholder="Kuch bhi poochho..." onkeydown="if(event.key==='Enter') send()">
  <button id="sendBtn" onclick="send()">Send</button>
  <button id="micBtn" onclick="toggleMic()">🎤</button>
  <button id="talkBtn" onclick="toggleTalk()">🔁 Talk</button>
</div>

<script>
// ── State ──────────────────────────────────────────────
let isListening   = false;
let isTalkMode    = false;
let recognition   = null;
let currentAudio  = null;

// ── Audio unlock (iOS / autoplay policy) ──────────────
document.addEventListener('click', () => {
  let a = new Audio();
  a.src = "data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAA";
  a.play().catch(() => {});
}, { once: true });

// ── UI helpers ────────────────────────────────────────
function setStatus(msg) {
  document.getElementById('status').textContent = msg;
}

function addMsg(text, cls) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = text;
  document.getElementById('chat').appendChild(div);
  scrollBottom();
}

function addImage(src) {
  const wrap = document.createElement('div');
  wrap.className = 'img-msg';
  const img = document.createElement('img');
  img.src = src;
  img.alt = 'Image';
  wrap.appendChild(img);
  document.getElementById('chat').appendChild(wrap);
  scrollBottom();
}

function scrollBottom() {
  const c = document.getElementById('chat');
  c.scrollTop = c.scrollHeight;
}

// ── Send message ───────────────────────────────────────
async function send() {
  const input = document.getElementById('text');
  const msg   = input.value.trim();
  if (!msg) return;

  addMsg(msg, 'user');
  input.value = '';
  setStatus('⏳ Thinking...');

  try {
    const res  = await fetch('/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: msg })
    });
    const data = await res.json();

    if (data.type === 'image') {
      addImage(data.image_url);
      setStatus('🖼️ Image loaded');
      if (isTalkMode) startListening();
      return;
    }

    addMsg(data.reply, 'ai');

    if (data.audio) {
      playAudio(data.audio, () => {
        // After AI finishes speaking → listen again in Talk mode
        if (isTalkMode) startListening();
      });
    } else {
      setStatus('Ready');
      if (isTalkMode) startListening();
    }

  } catch (e) {
    setStatus('❌ Error: ' + e.message);
    if (isTalkMode) startListening();
  }
}

// ── Audio playback ─────────────────────────────────────
function playAudio(b64, onEnd) {
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }

  const audio = new Audio('data:audio/mp3;base64,' + b64);
  currentAudio = audio;
  setStatus('🔊 Speaking...');

  audio.play().catch(e => {
    console.warn('Audio blocked:', e);
    setStatus('Ready');
    if (onEnd) onEnd();
  });

  audio.onended = () => {
    setStatus('Ready');
    if (onEnd) onEnd();
  };
}

// ── Single mic press ───────────────────────────────────
function toggleMic() {
  if (isListening) {
    stopListening();
  } else {
    startListening(true); // one-shot mode
  }
}

// ── Continuous Talk Mode ───────────────────────────────
function toggleTalk() {
  isTalkMode = !isTalkMode;
  const btn  = document.getElementById('talkBtn');

  if (isTalkMode) {
    btn.textContent = '⏹ Stop';
    btn.classList.add('active');
    setStatus('🎙️ Talk Mode ON — Boliye...');
    startListening();
  } else {
    btn.textContent = '🔁 Talk';
    btn.classList.remove('active');
    stopListening();
    setStatus('Talk Mode OFF');
  }
}

// ── Speech Recognition ─────────────────────────────────
function buildRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { alert('Chrome use karein for mic support!'); return null; }

  const r = new SR();
  r.lang          = 'hi-IN';   // handles Hindi + English both
  r.interimResults = false;
  r.maxAlternatives = 1;

  r.onstart = () => {
    isListening = true;
    document.getElementById('micBtn').classList.add('listening');
    setStatus('🎙️ Bol rahe ho... (sunne mein hun)');
  };

  r.onresult = (e) => {
    const text = e.results[0][0].transcript;
    document.getElementById('text').value = text;
    stopListening();
    send();
  };

  r.onerror = (e) => {
    console.warn('Mic error:', e.error);
    stopListening();
    setStatus('Mic error: ' + e.error);
  };

  r.onend = () => {
    stopListening();
  };

  return r;
}

function startListening(oneShot) {
  if (isListening) return;
  // Stop any playing audio before listening
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }

  recognition = buildRecognition();
  if (!recognition) return;

  try { recognition.start(); }
  catch(e) { console.warn(e); }
}

function stopListening() {
  isListening = false;
  document.getElementById('micBtn').classList.remove('listening');
  if (recognition) {
    try { recognition.stop(); } catch(e) {}
    recognition = null;
  }
}
</script>
</body>
</html>
"""

# ── Language detection ────────────────────────────────────────────
def detect_lang(text):
    hindi = "अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह"
    score = sum(1 for c in text if c in hindi)
    return "hi" if score > 2 else "en"

# ── TTS via edge-tts ──────────────────────────────────────────────
async def generate_voice(text, lang):
    voice = "hi-IN-SwaraNeural" if lang == "hi" else "en-US-JennyNeural"
    communicate = edge_tts.Communicate(text, voice)
    audio = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    return audio

def run_tts(text, lang):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_bytes = loop.run_until_complete(generate_voice(text, lang))
        return base64.b64encode(audio_bytes).decode()
    except Exception as e:
        print("TTS ERROR:", e)
        return None

# ── Image fetch — Wikimedia (free, no redirect issues) ────────────
WIKI_HEADERS = {"User-Agent": "KJMasterAI/1.0"}

def fetch_image(query):
    """Try multiple free image sources in order."""

    # 1. Picsum (always works, random photo)
    try:
        seed = abs(hash(query)) % 1000
        url  = f"https://picsum.photos/seed/{seed}/600/400"
        req  = urllib.request.Request(url, headers=WIKI_HEADERS)
        with urllib.request.urlopen(req, timeout=6) as r:
            raw = r.read()
            return "data:image/jpeg;base64," + base64.b64encode(raw).decode()
    except Exception as e:
        print("Picsum error:", e)

    # 2. Lorem Picsum by query hash fallback
    try:
        img_id = (abs(hash(query)) % 200) + 1
        url    = f"https://picsum.photos/id/{img_id}/600/400"
        req    = urllib.request.Request(url, headers=WIKI_HEADERS)
        with urllib.request.urlopen(req, timeout=6) as r:
            raw = r.read()
            return "data:image/jpeg;base64," + base64.b64encode(raw).decode()
    except Exception as e:
        print("Picsum fallback error:", e)

    return None

# ── Routes ────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg  = data.get("message", "")
    lang = detect_lang(msg)

    history.append({"role": "user", "content": msg})

    resp = client.chat.completions.create(
        model    = "llama-3.3-70b-versatile",
        messages = [{"role": "system", "content": SYSTEM}] + history,
        max_tokens  = 300,
        temperature = 0.7
    )

    reply = resp.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    # Check for image request — fixed regex (no extra backslashes)
    img_match = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
    if img_match:
        query = img_match.group(1)
        img   = fetch_image(query)
        return jsonify({
            "type":      "image",
            "image_url": img or ""
        })

    audio = run_tts(reply, lang)

    return jsonify({
        "reply": reply,
        "audio": audio
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
