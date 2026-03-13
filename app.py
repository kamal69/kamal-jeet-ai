import os
import base64
import asyncio
import urllib.request
import urllib.parse
import re
import json

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

IMPORTANT FORMATTING RULES:
- When sharing any code, ALWAYS wrap it in triple backticks like this:
  ```
  your code here
  ```
- Never put code inline without backticks.
- Use **bold** for important words.
- Keep explanations short and clear.

If user asks to show/dikhao any image or picture, reply EXACTLY like this (nothing else):
[IMAGE:object]

Examples:
User: show me a lion        -> Reply: [IMAGE:lion]
User: tiger dikhao          -> Reply: [IMAGE:tiger]
User: apple image           -> Reply: [IMAGE:apple]
User: Indian flag dikhao    -> Reply: [IMAGE:Indian flag]
User: Taj Mahal             -> Reply: [IMAGE:Taj Mahal]
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
  background: #0f172a; color: white;
  font-family: Arial, sans-serif;
  display: flex; flex-direction: column; height: 100vh; overflow: hidden;
}
header {
  background: linear-gradient(135deg, #1e293b, #334155);
  padding: 16px; text-align: center; font-size: 22px;
  font-weight: bold; border-bottom: 1px solid #475569;
}
#status {
  text-align: center; padding: 6px; font-size: 13px;
  color: #94a3b8; background: #1e293b; min-height: 28px;
}
#chat {
  flex: 1; overflow-y: auto; padding: 15px;
  display: flex; flex-direction: column; gap: 10px;
}
.msg {
  padding: 10px 14px; border-radius: 14px; max-width: 75%;
  line-height: 1.5; font-size: 15px;
  animation: fadeIn 0.3s ease; word-wrap: break-word;
}
@keyframes fadeIn {
  from { opacity:0; transform:translateY(8px); }
  to   { opacity:1; transform:translateY(0); }
}
.user { background:#2563eb; align-self:flex-end; border-bottom-right-radius:4px; }
.ai   { background:#334155; align-self:flex-start; border-bottom-left-radius:4px; }

/* ── Code blocks ── */
.msg pre {
  background: #0f172a;
  border: 1px solid #475569;
  border-radius: 8px;
  padding: 12px;
  margin: 8px 0 4px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre;
}
.msg code { font-family: 'Courier New', monospace; color: #7dd3fc; }
.msg pre code { color: #e2e8f0; display: block; }
.msg p { margin: 4px 0; }
.msg strong { color: #fbbf24; }
.copy-btn {
  display: inline-block; margin-top: 4px;
  padding: 3px 10px; font-size: 12px;
  background: #475569; color: #e2e8f0;
  border: none; border-radius: 6px; cursor: pointer;
}
.copy-btn:hover { background: #6366f1; }

.img-wrap { align-self:flex-start; animation: fadeIn 0.3s ease; }
.img-wrap img {
  max-width: 260px; border-radius: 12px;
  border: 2px solid #475569; display: block;
}
.img-wrap .img-label {
  font-size: 12px; color: #94a3b8; margin-top: 4px; padding-left: 2px;
}

#input {
  display:flex; padding:12px; background:#1e293b;
  gap:8px; border-top:1px solid #334155;
}
#text {
  flex:1; padding:12px; border-radius:12px;
  border:1px solid #475569; background:#0f172a;
  color:white; font-size:15px; outline:none;
}
#text:focus { border-color:#6366f1; }
button {
  padding:10px 16px; border:none; border-radius:12px;
  cursor:pointer; font-size:15px; font-weight:bold; transition:all 0.2s;
}
#sendBtn { background:#6366f1; color:white; }
#sendBtn:hover { background:#4f46e5; }
#micBtn  { background:#334155; color:white; min-width:46px; }
#micBtn.listening { background:#dc2626; animation:pulse 1s infinite; }
#talkBtn { background:#059669; color:white; }
#talkBtn.active { background:#dc2626; animation:pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }
</style>
</head>
<body>
<header>🤖 KJ Master AI</header>
<div id="status">Ready — Type karein ya 🎤 dabayein</div>
<div id="chat"></div>
<div id="input">
  <input id="text" placeholder="Kuch bhi poochho..." onkeydown="if(event.key==='Enter') send()">
  <button id="sendBtn" onclick="send()">Send</button>
  <button id="micBtn"  onclick="toggleMic()">🎤</button>
  <button id="talkBtn" onclick="toggleTalk()">🔁 Talk</button>
</div>
<script>
let isListening=false, isTalkMode=false, recognition=null, currentAudio=null;

document.addEventListener('click',()=>{
  let a=new Audio();
  a.src="data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAA";
  a.play().catch(()=>{});
},{once:true});

function setStatus(m){ document.getElementById('status').textContent=m; }

function escapeHtml(t){
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderMessage(text, cls){
  const d = document.createElement('div');
  d.className = 'msg ' + cls;

  if(cls === 'user'){
    d.textContent = text;
    document.getElementById('chat').appendChild(d);
    scrollBottom();
    return;
  }

  // Parse AI message: code blocks + basic markdown
  let html = '';
  // Split by triple-backtick code blocks
  const parts = text.split(/(```[\s\S]*?```)/g);
  parts.forEach(part => {
    if(part.startsWith('```') && part.endsWith('```')){
      // Code block
      let inner = part.slice(3, -3);
      // Remove optional language tag on first line
      const newline = inner.indexOf('\\n');
      if(newline !== -1){
        const firstLine = inner.slice(0, newline).trim();
        if(firstLine && !/\\s/.test(firstLine) && firstLine.length < 20){
          inner = inner.slice(newline + 1);
        }
      }
      const codeId = 'code_' + Math.random().toString(36).slice(2,7);
      html += '<pre><code id="' + codeId + '">' + escapeHtml(inner.trim()) + '</code></pre>';
      html += '<button class="copy-btn" onclick="copyCode(\\''+codeId+'\\')">📋 Copy</button>';
    } else {
      // Normal text — handle inline formatting
      let t = escapeHtml(part);
      // Bold **text**
      t = t.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
      // Inline code `code`
      t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
      // Line breaks
      t = t.replace(/\\n/g, '<br>');
      html += '<p>' + t + '</p>';
    }
  });

  d.innerHTML = html;
  document.getElementById('chat').appendChild(d);
  scrollBottom();
}

function addMsg(text, cls){ renderMessage(text, cls); }

function copyCode(id){
  const el = document.getElementById(id);
  if(!el) return;
  navigator.clipboard.writeText(el.innerText).then(()=>{
    const btn = el.parentElement.nextSibling;
    if(btn){ btn.textContent = '✅ Copied!'; setTimeout(()=>{ btn.textContent='📋 Copy'; },2000); }
  });
}

function addImage(src,label){
  const wrap=document.createElement('div');
  wrap.className='img-wrap';
  const img=document.createElement('img');
  img.src=src; img.alt=label||'Image';
  img.onerror=()=>{ wrap.innerHTML='<div class="msg ai">❌ Image load nahi hui — '+label+'</div>'; };
  const lbl=document.createElement('div');
  lbl.className='img-label'; lbl.textContent='🖼️ '+(label||'Image');
  wrap.appendChild(img); wrap.appendChild(lbl);
  document.getElementById('chat').appendChild(wrap);
  scrollBottom();
}

function scrollBottom(){
  const c=document.getElementById('chat'); c.scrollTop=c.scrollHeight;
}

async function send(){
  const input=document.getElementById('text');
  const msg=input.value.trim(); if(!msg) return;
  addMsg(msg,'user'); input.value=''; setStatus('⏳ Soch raha hun...');
  try{
    const res=await fetch('/chat',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:msg})
    });
    const data=await res.json();
    if(data.type==='image'){
      if(data.image_url){ addImage(data.image_url, data.query); }
      else { addMsg('❌ Image nahi mili: '+data.query,'ai'); }
      setStatus('Ready');
      if(isTalkMode) startListening();
      return;
    }
    addMsg(data.reply,'ai');
    if(data.audio){
      playAudio(data.audio,()=>{ if(isTalkMode) startListening(); });
    } else {
      setStatus('Ready');
      if(isTalkMode) startListening();
    }
  } catch(e){
    addMsg('❌ Error: '+e.message,'ai'); setStatus('Error');
    if(isTalkMode) startListening();
  }
}

function playAudio(b64,onEnd){
  if(currentAudio){currentAudio.pause();currentAudio=null;}
  const audio=new Audio('data:audio/mp3;base64,'+b64);
  currentAudio=audio; setStatus('🔊 Bol raha hun...');
  audio.play().catch(e=>{ console.warn(e); setStatus('Ready'); if(onEnd) onEnd(); });
  audio.onended=()=>{ setStatus('Ready'); if(onEnd) onEnd(); };
}

function toggleMic(){ if(isListening) stopListening(); else startListening(); }

function toggleTalk(){
  isTalkMode=!isTalkMode;
  const btn=document.getElementById('talkBtn');
  if(isTalkMode){
    btn.textContent='⏹ Stop'; btn.classList.add('active');
    setStatus('🎙️ Talk Mode ON — Boliye...');
    startListening();
  } else {
    btn.textContent='🔁 Talk'; btn.classList.remove('active');
    stopListening(); setStatus('Talk Mode OFF');
  }
}

function buildRecognition(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){ alert('Chrome use karein mic ke liye!'); return null; }
  const r=new SR();
  r.lang='hi-IN'; r.interimResults=false; r.maxAlternatives=1;
  r.onstart=()=>{ isListening=true; document.getElementById('micBtn').classList.add('listening'); setStatus('🎙️ Sun raha hun...'); };
  r.onresult=(e)=>{ const t=e.results[0][0].transcript; document.getElementById('text').value=t; stopListening(); send(); };
  r.onerror=(e)=>{ console.warn(e.error); stopListening(); setStatus('Mic error: '+e.error); };
  r.onend=()=>{ stopListening(); };
  return r;
}

function startListening(){
  if(isListening) return;
  if(currentAudio){currentAudio.pause();currentAudio=null;}
  recognition=buildRecognition(); if(!recognition) return;
  try{ recognition.start(); } catch(e){ console.warn(e); }
}

function stopListening(){
  isListening=false;
  document.getElementById('micBtn').classList.remove('listening');
  if(recognition){ try{recognition.stop();}catch(e){} recognition=null; }
}
</script>
</body>
</html>
"""

# ── Language detection ────────────────────────────────────────────
def detect_lang(text):
    hindi = "अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह"
    return "hi" if sum(1 for c in text if c in hindi) > 2 else "en"

# ── TTS ───────────────────────────────────────────────────────────
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

# ── Image fetch ───────────────────────────────────────────────────
HEADERS = {"User-Agent": "KJMasterAI/2.0 (educational project)"}

def fetch_wikipedia_image(query):
    """Get main image from Wikipedia page."""
    try:
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": query,
            "prop": "pageimages", "pithumbsize": 600,
            "format": "json", "redirects": 1
        })
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            for page in data.get("query", {}).get("pages", {}).values():
                thumb = page.get("thumbnail", {}).get("source")
                if thumb:
                    img_req = urllib.request.Request(thumb, headers=HEADERS)
                    with urllib.request.urlopen(img_req, timeout=8) as ir:
                        raw = ir.read()
                        mime = ir.headers.get("Content-Type","image/jpeg").split(";")[0]
                        return f"data:{mime};base64," + base64.b64encode(raw).decode()
    except Exception as e:
        print("Wikipedia error:", e)
    return None

def fetch_wikimedia_image(query):
    """Search Wikimedia Commons for image."""
    try:
        search_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "list": "search",
            "srnamespace": 6, "srsearch": query,
            "srlimit": 5, "format": "json"
        })
        req = urllib.request.Request(search_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            results = data.get("query", {}).get("search", [])
            for result in results:
                title = result.get("title", "")
                if not title.startswith("File:"):
                    continue
                # Skip SVG and non-image files
                low = title.lower()
                if any(low.endswith(ext) for ext in [".svg", ".ogg", ".ogv", ".webm"]):
                    continue
                file_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
                    "action": "query", "titles": title,
                    "prop": "imageinfo", "iiprop": "url",
                    "iiurlwidth": 600, "format": "json"
                })
                freq = urllib.request.Request(file_url, headers=HEADERS)
                with urllib.request.urlopen(freq, timeout=8) as fr:
                    fdata = json.loads(fr.read().decode())
                    for fp in fdata.get("query", {}).get("pages", {}).values():
                        ii = fp.get("imageinfo", [])
                        if ii and ii[0].get("url"):
                            thumb = ii[0]["url"]
                            img_req = urllib.request.Request(thumb, headers=HEADERS)
                            with urllib.request.urlopen(img_req, timeout=8) as ir:
                                raw = ir.read()
                                mime = ir.headers.get("Content-Type","image/jpeg").split(";")[0]
                                if "image" in mime:
                                    return f"data:{mime};base64," + base64.b64encode(raw).decode()
    except Exception as e:
        print("Wikimedia error:", e)
    return None

def fetch_image(query):
    print(f"Image fetch: '{query}'")
    result = fetch_wikipedia_image(query)
    if result:
        print("✓ Wikipedia")
        return result
    result = fetch_wikimedia_image(query)
    if result:
        print("✓ Wikimedia Commons")
        return result
    print("✗ Not found")
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
        model       = "llama-3.3-70b-versatile",
        messages    = [{"role": "system", "content": SYSTEM}] + history,
        max_tokens  = 300,
        temperature = 0.7
    )

    reply = resp.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    img_match = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
    if img_match:
        query = img_match.group(1).strip()
        img   = fetch_image(query)
        return jsonify({"type": "image", "image_url": img or "", "query": query})

    audio = run_tts(reply, lang)
    return jsonify({"reply": reply, "audio": audio})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
