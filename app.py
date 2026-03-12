"""
=============================================================
    KAMAL JEET - AI AVATAR WEB APP
    Version: 1.0 | Flask + Groq + Edge TTS
    Run: python app.py
    Then open: http://localhost:5000
=============================================================
"""

import os
import re
import json
import asyncio
import urllib.request
import urllib.parse
import base64
from io import BytesIO
from flask import Flask, request, jsonify, render_template_string
from groq import Groq
import edge_tts

# =============================================================
#                     CONFIGURATION
# =============================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
AI_MODEL     = "llama-3.1-8b-instant"
TTS_VOICE_EN = "en-US-AriaNeural"
TTS_VOICE_HI = "hi-IN-MadhurNeural"
MAX_TOKENS   = 500

SYSTEM_PROMPT = """You are a professional bilingual AI assistant named Kamal Jeet.

Language Rules:
- If the user writes in pure/shuddh Hindi (Devanagari script), reply in pure shuddh Hindi only.
- If the user writes in Hinglish (Roman script Hindi), reply in Hinglish only.
- If the user writes in English, reply in professional English only.
- Never mix styles.

Formatting Rules:
- NEVER use markdown like **bold**, *italic*, bullet points, or backticks.
- Write in plain simple conversational text only.

Image Rules:
- Whenever user asks for ANY image, photo, picture, show me, dikhao — ALWAYS reply ONLY with: [IMAGE:search_term]
- Examples: "show me apple" → [IMAGE:apple fruit] | "Taj Mahal dikhao" → [IMAGE:Taj Mahal India]
- NEVER say you cannot show images. ALWAYS use [IMAGE:] tag.

Always be concise, helpful, and professional."""

# =============================================================
#                     FLASK APP
# =============================================================

app          = Flask(__name__)
client       = Groq(api_key=GROQ_API_KEY)
chat_history = []

# =============================================================
#                     HTML TEMPLATE
# =============================================================

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Kamal Jeet — AI Assistant</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

  :root {
    --bg:      #0D0F14;
    --panel:   #13151C;
    --input:   #1A1D27;
    --user:    #1E3A5F;
    --ai:      #1A1D27;
    --accent:  #00D4FF;
    --accent2: #7B61FF;
    --text:    #E8EAF0;
    --dim:     #6B7280;
    --border:  #2A2D3A;
    --green:   #10B981;
    --red:     #EF4444;
  }

  * { margin:0; padding:0; box-sizing:border-box; }

  body {
    font-family: 'JetBrains Mono', monospace;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  header {
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    padding: 14px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }

  .logo { display: flex; align-items: center; gap: 10px; }
  .dot  { width:10px; height:10px; border-radius:50%; background:var(--accent); animation: pulse 2s infinite; }

  @keyframes pulse {
    0%,100% { opacity:1; }
    50%      { opacity:0.4; }
  }

  .logo h1  { font-size:18px; color:var(--accent); letter-spacing:2px; }
  .logo p   { font-size:9px;  color:var(--dim); margin-top:2px; }

  .controls { display:flex; align-items:center; gap:12px; }

  .toggle-btn {
    background: var(--input);
    border: 1px solid var(--border);
    color: var(--dim);
    padding: 6px 14px;
    border-radius: 6px;
    font-family: inherit;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .toggle-btn.active { color:var(--accent); border-color:var(--accent); }
  .toggle-btn:hover  { background:var(--border); }

  .clear-btn {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--dim);
    padding: 6px 14px;
    border-radius: 6px;
    font-family: inherit;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .clear-btn:hover { border-color:var(--red); color:var(--red); }

  #chat {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    scroll-behavior: smooth;
  }

  #chat::-webkit-scrollbar       { width:4px; }
  #chat::-webkit-scrollbar-track { background:var(--bg); }
  #chat::-webkit-scrollbar-thumb { background:var(--border); border-radius:4px; }

  .msg-wrap { margin-bottom: 18px; display:flex; flex-direction:column; }
  .msg-wrap.user  { align-items: flex-end; }
  .msg-wrap.ai    { align-items: flex-start; }
  .msg-wrap.system{ align-items: center; }

  .meta {
    font-size: 9px;
    color: var(--dim);
    margin-bottom: 4px;
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .msg-wrap.user .meta  { flex-direction:row-reverse; }
  .meta .name           { font-weight:700; }
  .meta .name.user-name { color:var(--accent); }
  .meta .name.ai-name   { color:var(--accent2); }

  .bubble {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 13px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .bubble.user   { background:var(--user); color:#93C5FD; }
  .bubble.ai     { background:var(--ai);   color:#C4B5FD; border:1px solid var(--border); }
  .bubble.system { background:transparent; color:var(--dim); font-size:11px; text-align:center; }

  .bubble img {
    max-width: 100%;
    border-radius: 8px;
    display: block;
    margin-bottom: 6px;
  }

  .img-caption { font-size:10px; color:var(--dim); margin-top:4px; }

  .typing-dots span {
    display:inline-block;
    width:6px; height:6px;
    background:var(--accent2);
    border-radius:50%;
    margin:0 2px;
    animation: bounce 1.2s infinite;
  }
  .typing-dots span:nth-child(2) { animation-delay:0.2s; }
  .typing-dots span:nth-child(3) { animation-delay:0.4s; }
  @keyframes bounce {
    0%,80%,100% { transform:translateY(0); }
    40%          { transform:translateY(-6px); }
  }

  .input-area {
    background: var(--panel);
    border-top: 1px solid var(--border);
    padding: 14px 20px;
    flex-shrink: 0;
  }

  .input-row {
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }

  #userInput {
    flex: 1;
    background: var(--input);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: inherit;
    font-size: 13px;
    padding: 12px 16px;
    border-radius: 8px;
    resize: none;
    outline: none;
    min-height: 46px;
    max-height: 120px;
    transition: border-color 0.2s;
  }
  #userInput:focus { border-color:var(--accent); }

  #sendBtn {
    background: var(--accent);
    color: var(--bg);
    border: none;
    padding: 12px 22px;
    border-radius: 8px;
    font-family: inherit;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }
  #sendBtn:hover    { background:var(--accent2); color:white; }
  #sendBtn:disabled { opacity:0.5; cursor:not-allowed; }

  .hint { font-size:9px; color:var(--dim); text-align:center; margin-top:8px; }

  .status-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 9px;
    color: var(--dim);
    margin-bottom: 6px;
  }
  .status-dot { width:6px; height:6px; border-radius:50%; background:var(--green); }
  .status-dot.busy { background:var(--red); animation:pulse 1s infinite; }

  @media (max-width: 600px) {
    .bubble { max-width:90%; font-size:12px; }
    header  { padding:10px 14px; }
    .logo h1{ font-size:15px; }
  }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="dot"></div>
    <div>
      <h1>KAMAL JEET</h1>
      <p>AI Avatar Assistant &nbsp;•&nbsp; Groq Powered ⚡</p>
    </div>
  </div>
  <div class="controls">
    <button class="toggle-btn active" id="voiceBtn" onclick="toggleVoice()">🔊 Voice ON</button>
    <button class="clear-btn" onclick="clearChat()">Clear</button>
  </div>
</header>

<div id="chat"></div>

<div class="input-area">
  <div class="status-bar">
    <div class="status-dot" id="statusDot"></div>
    <span id="statusText">Ready</span>
  </div>
  <div class="input-row">
    <textarea id="userInput" placeholder="Type in English, Hindi, or Hinglish..." rows="1"
              onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
    <button id="sendBtn" onclick="sendMessage()">Send ➤</button>
  </div>
  <div class="hint">Enter to send &nbsp;•&nbsp; Shift+Enter for new line &nbsp;•&nbsp; Supports Hindi / Hinglish / English</div>
</div>

<script>
  let voiceEnabled = true;

  function toggleVoice() {
    voiceEnabled = !voiceEnabled;
    const btn = document.getElementById('voiceBtn');
    btn.textContent = voiceEnabled ? '🔊 Voice ON' : '🔇 Voice OFF';
    btn.classList.toggle('active', voiceEnabled);
  }

  function setStatus(text, busy=false) {
    document.getElementById('statusText').textContent = text;
    document.getElementById('statusDot').className = 'status-dot' + (busy ? ' busy' : '');
  }

  function getTime() {
    return new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
  }

  function addMessage(content, sender, isImage=false, imageUrl=null, caption=null) {
    const chat = document.getElementById('chat');
    const wrap = document.createElement('div');
    wrap.className = 'msg-wrap ' + sender;

    let metaHtml = '';
    if (sender !== 'system') {
      const name     = sender === 'user' ? 'You' : 'Kamal Jeet';
      const nameClass= sender === 'user' ? 'user-name' : 'ai-name';
      metaHtml = `<div class="meta"><span class="name ${nameClass}">${name}</span><span>${getTime()}</span></div>`;
    }

    let bubbleContent = '';
    if (isImage && imageUrl) {
      bubbleContent = `<img src="${imageUrl}" alt="${caption}" loading="lazy"><div class="img-caption">"${caption}"</div>`;
    } else {
      bubbleContent = escapeHtml(content);
    }

    wrap.innerHTML = metaHtml + `<div class="bubble ${sender}">${bubbleContent}</div>`;
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
    return wrap;
  }

  function addTyping() {
    const chat = document.getElementById('chat');
    const wrap = document.createElement('div');
    wrap.className = 'msg-wrap ai';
    wrap.id = 'typing';
    wrap.innerHTML = `
      <div class="meta"><span class="name ai-name">Kamal Jeet</span></div>
      <div class="bubble ai"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
  }

  function removeTyping() {
    const t = document.getElementById('typing');
    if (t) t.remove();
  }

  function escapeHtml(text) {
    return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }

  async function sendMessage() {
    const input = document.getElementById('userInput');
    const text  = input.value.trim();
    if (!text) return;

    input.value = '';
    input.style.height = 'auto';
    document.getElementById('sendBtn').disabled = true;
    setStatus('Processing...', true);

    addMessage(text, 'user');
    addTyping();

    try {
      const res  = await fetch('/chat', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({message: text, voice: voiceEnabled})
      });
      const data = await res.json();
      removeTyping();

      if (data.type === 'image') {
        addMessage('', 'ai', true, data.image_url, data.caption);
      } else {
        addMessage(data.reply, 'ai');
        if (voiceEnabled && data.audio) {
          const audio = new Audio('data:audio/mp3;base64,' + data.audio);
          audio.play();
        }
      }
      setStatus('Ready');
    } catch (err) {
      removeTyping();
      addMessage('Error: Could not connect. Please try again.', 'ai');
      setStatus('Error', true);
    }

    document.getElementById('sendBtn').disabled = false;
    document.getElementById('userInput').focus();
  }

  function clearChat() {
    fetch('/clear', {method:'POST'});
    document.getElementById('chat').innerHTML = '';
    addMessage('Chat cleared. Start a new conversation!', 'system');
  }

  addMessage('Welcome! I am Kamal Jeet — your AI assistant.\\nChat in English, Hindi (हिंदी), or Hinglish. I will match your language automatically. 🎙️', 'system');
  document.getElementById('userInput').focus();
</script>
</body>
</html>"""

# =============================================================
#                     HELPER FUNCTIONS
# =============================================================

def detect_language(text: str) -> str:
    hindi_chars = set('अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसहक्षत्रज्ञ')
    return "hi" if any(c in hindi_chars for c in text) else "en"


def clean_text(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*',     r'\1', text)
    text = re.sub(r'`(.*?)`',       r'\1', text)
    text = re.sub(r'#{1,6}\s',      '',    text)
    text = re.sub(r'^\s*[-*]\s', '', text, flags=re.MULTILINE)
    return text.strip()


def fetch_image_base64(query: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query.replace(' ', '_'))}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            data    = json.loads(r.read())
            img_url = (data.get("thumbnail") or data.get("originalimage") or {}).get("source")
        if img_url:
            with urllib.request.urlopen(urllib.request.Request(img_url, headers=headers), timeout=8) as r:
                return "data:image/jpeg;base64," + base64.b64encode(r.read()).decode()
    except Exception:
        pass

    try:
        url  = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}"
        req  = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode("utf-8")
        matches = re.findall(r'murl&quot;:&quot;(https?://[^&]+\.(?:jpg|jpeg|png))&quot;', html)
        if matches:
            with urllib.request.urlopen(urllib.request.Request(matches[0], headers=headers), timeout=8) as r:
                return "data:image/jpeg;base64," + base64.b64encode(r.read()).decode()
    except Exception:
        pass
    return None


async def generate_voice_async(text: str):
    try:
        lang  = detect_language(text)
        voice = TTS_VOICE_HI if lang == "hi" else TTS_VOICE_EN
        buf   = BytesIO()
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


# =============================================================
#                     ROUTES
# =============================================================

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/chat", methods=["POST"])
def chat():
    data         = request.json
    user_message = data.get("message", "")
    want_voice   = data.get("voice", True)

    chat_history.append({"role": "user", "content": user_message})
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + chat_history,
            max_tokens=MAX_TOKENS,
            temperature=0.7
        )
        reply = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": reply})
        if len(chat_history) > 20:
            chat_history.pop(0); chat_history.pop(0)
    except Exception as e:
        return jsonify({"type": "text", "reply": f"Error: {str(e)}"})

    image_match = re.match(r'^\[IMAGE:(.*?)\]$', reply.strip())
    if image_match:
        query     = image_match.group(1)
        image_url = fetch_image_base64(query)
        return jsonify({"type": "image", "image_url": image_url, "caption": query})

    reply = clean_text(reply)

    audio_b64 = None
    if want_voice:
        audio_b64 = asyncio.run(generate_voice_async(reply))

    return jsonify({"type": "text", "reply": reply, "audio": audio_b64})


@app.route("/clear", methods=["POST"])
def clear():
    chat_history.clear()
    return jsonify({"status": "ok"})


# =============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("  Kamal Jeet AI — Web App Started!")
    print(f"  Open in browser: http://localhost:{port}")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)
