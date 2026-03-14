import os
import base64
import urllib.request
import urllib.parse
import re
import json

from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs

load_dotenv()

app = Flask(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

history = []

# ================= SYSTEM PROMPT =================

SYSTEM = """
You are Sarthi AI - a friendly, smart AI assistant made by Kamal Jeet.
You understand Hindi, English and Hinglish fluently.
Always reply in the same language the user speaks.
Keep replies short and natural for voice conversation.
If user asks for an image, reply ONLY with: [IMAGE:search query]
"""

# ================= HTML =================

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sarthi AI</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:        #0d0d0d;
  --sidebar:   #111111;
  --surface:   #1a1a1a;
  --surface2:  #222222;
  --border:    #2a2a2a;
  --accent:    #c96442;
  --accent2:   #e07a52;
  --text:      #ececec;
  --text-muted:#888;
  --code-bg:   #161616;
  --radius:    12px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Sora', sans-serif;
  display: flex;
  height: 100vh;
}

/* ── Sidebar ── */
#sidebar {
  width: 240px;
  background: var(--sidebar);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 20px 14px;
  gap: 8px;
  flex-shrink: 0;
}
.logo {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px 18px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 6px;
}
.logo-text { font-size: 15px; font-weight: 600; letter-spacing: -0.3px; }
.logo-sub  { font-size: 10px; color: var(--text-muted); font-weight: 300; }
.new-chat-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 12px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: 'Sora', sans-serif;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.18s;
  width: 100%;
  text-align: left;
}
.new-chat-btn:hover { background: var(--surface); border-color: var(--accent); }
.sidebar-label {
  font-size: 10px; font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 1px;
  padding: 8px 10px 4px;
}
.chat-item {
  padding: 8px 10px; border-radius: 8px;
  font-size: 12.5px; color: var(--text-muted);
  cursor: pointer; transition: all 0.15s;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.chat-item:hover, .chat-item.active { background: var(--surface2); color: var(--text); }
.sidebar-bottom {
  margin-top: auto; padding-top: 12px;
  border-top: 1px solid var(--border);
}
.user-pill {
  display: flex; align-items: center; gap: 9px;
  padding: 8px 10px; border-radius: 8px;
  cursor: pointer; transition: background 0.15s;
}
.user-pill:hover { background: var(--surface2); }
.user-avatar {
  width: 28px; height: 28px;
  background: linear-gradient(135deg, var(--accent), #7c3aed);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; flex-shrink: 0;
}
.user-name { font-size: 12.5px; font-weight: 500; }

/* ── Main ── */
#main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

/* ── Topbar ── */
#topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg); flex-shrink: 0;
}
.model-badge {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 12px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 20px; font-size: 12px; color: var(--text-muted);
}
.model-dot { width: 6px; height: 6px; background: #22c55e; border-radius: 50%; }
#status-pill {
  font-size: 12px; color: var(--text-muted);
  padding: 4px 12px; border-radius: 20px;
  background: var(--surface); border: 1px solid var(--border);
  transition: all 0.2s;
}

/* ── Chat ── */
#chat {
  flex: 1; overflow-y: auto;
  padding: 32px 0;
  display: flex; flex-direction: column;
  scroll-behavior: smooth;
}
#chat::-webkit-scrollbar { width: 4px; }
#chat::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

/* ── Welcome ── */
#welcome {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 16px; padding: 40px; text-align: center;
}
.welcome-icon {
  width: 56px; height: 56px;
  background: linear-gradient(135deg, var(--accent), #9333ea);
  border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
  box-shadow: 0 0 40px rgba(201,100,66,0.25);
}
.welcome-title { font-size: 26px; font-weight: 600; letter-spacing: -0.5px; }
.welcome-sub   { font-size: 14px; color: var(--text-muted); max-width: 360px; line-height: 1.6; }
.suggestion-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 10px; margin-top: 8px;
  width: 100%; max-width: 500px;
}
.suggestion-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 12px 14px;
  font-size: 13px; color: var(--text-muted);
  cursor: pointer; transition: all 0.18s; text-align: left; line-height: 1.4;
}
.suggestion-card:hover { border-color: var(--accent); color: var(--text); background: var(--surface2); }
.suggestion-card strong { display: block; color: var(--text); font-size: 12px; margin-bottom: 3px; }

/* ── Message rows ── */
.msg-row {
  padding: 16px 24px; display: flex; gap: 14px;
  animation: fadeUp 0.25s ease;
  max-width: 820px; width: 100%; margin: 0 auto;
}
.msg-row.user-row { flex-direction: row-reverse; }
@keyframes fadeUp {
  from { opacity:0; transform:translateY(10px); }
  to   { opacity:1; transform:translateY(0); }
}
.avatar {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600; margin-top: 2px;
}
.ai-avatar    { background: linear-gradient(135deg, var(--accent), #9333ea); }
.user-avatar2 { background: linear-gradient(135deg, #2563eb, #7c3aed); }
.bubble {
  max-width: 680px; font-size: 14.5px;
  line-height: 1.75; color: var(--text); word-wrap: break-word;
}
.user-row .bubble {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 16px 4px 16px 16px; padding: 11px 16px;
}
.bubble p { margin: 0 0 8px; }
.bubble p:last-child { margin-bottom: 0; }
.bubble strong { color: #fbbf24; font-weight: 600; }
.bubble code {
  font-family: 'JetBrains Mono', monospace;
  background: var(--code-bg); color: #7dd3fc;
  padding: 2px 6px; border-radius: 5px; font-size: 13px;
}
.code-block-wrap {
  margin: 10px 0 6px; border-radius: 10px;
  overflow: hidden; border: 1px solid var(--border);
}
.code-header {
  display: flex; align-items: center; justify-content: space-between;
  background: #1c1c1c; padding: 7px 14px;
  font-size: 11px; color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}
.bubble pre {
  background: var(--code-bg); padding: 14px 16px;
  overflow-x: auto; font-size: 13px; line-height: 1.65;
  white-space: pre; margin: 0;
}
.bubble pre code { background: none; padding: 0; color: #e2e8f0; font-size: 13px; }
.copy-btn {
  background: var(--surface2); border: 1px solid var(--border);
  color: var(--text-muted); padding: 3px 10px;
  border-radius: 5px; font-size: 11px; cursor: pointer;
  font-family: 'Sora', sans-serif; transition: all 0.15s;
}
.copy-btn:hover { border-color: var(--accent); color: var(--text); }
.img-wrap { margin-top: 4px; }
.img-wrap img {
  max-width: 300px; border-radius: var(--radius);
  border: 1px solid var(--border); display: block;
}
.img-label { font-size: 11px; color: var(--text-muted); margin-top: 5px; }
.typing-dots { display: flex; gap: 5px; padding: 8px 0; align-items: center; }
.typing-dots span {
  width: 7px; height: 7px; background: var(--text-muted);
  border-radius: 50%; animation: blink 1.2s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,80%,100%{opacity:0.2} 40%{opacity:1} }

/* ── Input ── */
#input-area {
  padding: 16px 24px 20px;
  background: var(--bg); border-top: 1px solid var(--border); flex-shrink: 0;
}
.input-box {
  max-width: 820px; margin: 0 auto;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px;
  display: flex; align-items: flex-end;
  gap: 8px; padding: 10px 12px;
  transition: border-color 0.2s;
}
.input-box:focus-within { border-color: var(--accent); }
#text {
  flex: 1; background: none; border: none; outline: none;
  color: var(--text); font-family: 'Sora', sans-serif;
  font-size: 14px; line-height: 1.5;
  resize: none; height: 28px; min-height: 28px; max-height: 140px;
  padding: 3px 4px; overflow-y: hidden;
}
#text::placeholder { color: var(--text-muted); }
.icon-btn {
  width: 36px; height: 36px; border: none; border-radius: 9px;
  background: var(--surface2); color: var(--text-muted);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  font-size: 16px; transition: all 0.17s; flex-shrink: 0;
}
.icon-btn:hover { background: var(--border); color: var(--text); }
.icon-btn.active { background: #dc2626; color: white; animation: pulse 1s infinite; }
#sendBtn {
  width: 36px; height: 36px; border: none; border-radius: 9px;
  background: var(--accent); color: white; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; transition: all 0.17s; flex-shrink: 0;
}
#sendBtn:hover { background: var(--accent2); transform: scale(1.05); }
#sendBtn:active { transform: scale(0.97); }
#talkBtn {
  padding: 0 14px; height: 36px; border: none; border-radius: 9px;
  background: var(--surface2); border: 1px solid var(--border);
  color: var(--text-muted); cursor: pointer;
  font-family: 'Sora', sans-serif; font-size: 12px; font-weight: 500;
  transition: all 0.17s; flex-shrink: 0; white-space: nowrap;
}
#talkBtn:hover  { border-color: #22c55e; color: #22c55e; }
#talkBtn.active { background: #dc2626; border-color: #dc2626; color: white; animation: pulse 1s infinite; }
.input-hint {
  text-align: center; font-size: 11px; color: var(--text-muted);
  margin-top: 8px; max-width: 820px; margin-left: auto; margin-right: auto;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }

@media(max-width: 640px){
  #sidebar { display: none; }
  .msg-row { padding: 12px 14px; }
  .input-box { border-radius: 12px; }
  #input-area { padding: 12px 14px 16px; }
}
</style>
</head>
<body>

<!-- Sidebar -->
<div id="sidebar">
  <div class="logo">
    <div style="width:32px;height:32px;flex-shrink:0;">
      <svg width="32" height="32" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
        <rect width="36" height="36" rx="10" fill="#1a1a1a" stroke="#2a2a2a" stroke-width="1"/>
        <circle cx="18" cy="18" r="10" fill="none" stroke="#c96442" stroke-width="1.5"/>
        <circle cx="18" cy="18" r="6" fill="#c96442" opacity="0.15"/>
        <polygon points="18,8 20,14 18,12 16,14" fill="#c96442"/>
        <polygon points="18,28 20,22 18,24 16,22" fill="#444"/>
        <polygon points="28,18 22,20 24,18 22,16" fill="#444"/>
        <polygon points="8,18 14,20 12,18 14,16" fill="#444"/>
        <circle cx="18" cy="18" r="2.5" fill="#c96442"/>
      </svg>
    </div>
    <div>
      <div class="logo-text">Sarthi AI</div>
      <div class="logo-sub">Powered by Kamal Jeet</div>
    </div>
  </div>

  <button class="new-chat-btn" onclick="newChat()">✏️ &nbsp; New Chat</button>

  <div class="sidebar-label">Recent</div>
  <div class="chat-item active" id="currentChatLabel">New conversation</div>

  <div class="sidebar-bottom">
    <div class="user-pill">
      <div class="user-avatar">KJ</div>
      <div>
        <div class="user-name">Kamal Jeet</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:1px;">📍 Himachal Pradesh</div>
      </div>
    </div>
  </div>
</div>

<!-- Main -->
<div id="main">
  <div id="topbar">
    <div class="model-badge">
      <div class="model-dot"></div>
      Online
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      <button onclick="clearChat()"
        style="background:none;border:1px solid var(--border);color:var(--text-muted);padding:5px 12px;border-radius:20px;cursor:pointer;font-size:12px;font-family:'Sora',sans-serif;transition:all 0.15s;"
        onmouseover="this.style.borderColor='#ef4444';this.style.color='#ef4444'"
        onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--text-muted)'">
        🗑️ Clear
      </button>
      <div id="status-pill">Ready</div>
    </div>
  </div>

  <div id="chat">
    <div id="welcome">
      <div class="welcome-icon">🤖</div>
      <div class="welcome-title">Sarthi AI</div>
      <div class="welcome-sub">Hindi, English, Hinglish — sab samajhta hun.</div>
      <div class="suggestion-grid">
        <div class="suggestion-card" onclick="suggest('Python mein inheritance kya hota hai?')">
          <strong>💻 Code Seekhein</strong>Python inheritance explain karo
        </div>
        <div class="suggestion-card" onclick="suggest('Taj Mahal ki image dikhao')">
          <strong>🖼️ Image Dekho</strong>Taj Mahal dikhao
        </div>
        <div class="suggestion-card" onclick="suggest('Aaj ka weather kaisa hai?')">
          <strong>💬 Baat Karein</strong>Koi bhi sawaal poochho
        </div>
        <div class="suggestion-card" onclick="suggest('Mujhe motivate karo')">
          <strong>✨ Motivation</strong>Motivational quote do
        </div>
      </div>
    </div>
  </div>

  <div id="input-area">
    <div class="input-box">
      <textarea id="text" placeholder="Kuch bhi poochho…"></textarea>
      <button class="icon-btn" id="micBtn" title="Mic">🎤</button>
      <button id="talkBtn">🔁 Talk</button>
      <button id="sendBtn" title="Send">➤</button>
    </div>
    <div class="input-hint">Enter to send · Shift+Enter for new line · 🎤 for voice</div>
  </div>
</div>

<script>
// ── State ──
let isListening = false;
let isTalkMode  = false;
let recognition = null;
let currentAudio = null;
let msgCount = 0;

// ── Wire up buttons after DOM ready ──
document.addEventListener('DOMContentLoaded', function() {
  const textEl  = document.getElementById('text');
  const sendBtn = document.getElementById('sendBtn');
  const micBtn  = document.getElementById('micBtn');
  const talkBtn = document.getElementById('talkBtn');

  // Auto-resize textarea
  textEl.addEventListener('input', function() {
    this.style.height = '28px';
    const sh = this.scrollHeight;
    this.style.height = Math.min(sh, 140) + 'px';
    this.style.overflowY = sh > 140 ? 'auto' : 'hidden';
  });

  // Enter to send, Shift+Enter for newline
  textEl.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  // Send button click
  sendBtn.addEventListener('click', function() {
    send();
  });

  // Mic button
  micBtn.addEventListener('click', function() {
    toggleMic();
  });

  // Talk button
  talkBtn.addEventListener('click', function() {
    toggleTalk();
  });
});

// ── Unlock autoplay on first click ──
document.addEventListener('click', () => {
  const a = new Audio();
  a.src = "data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAA";
  a.play().catch(() => {});
}, { once: true });

// ── Safe TTS cancel ──
function cancelSpeech() {
  try {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  } catch(e) { console.warn('TTS cancel error:', e); }
}

function setStatus(m) {
  document.getElementById('status-pill').textContent = m;
}

function suggest(text) {
  const el = document.getElementById('text');
  el.value = text;
  el.style.height = '28px';
  send();
}

// ── Escape HTML ──
function esc(t) {
  return (t || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Render markdown ──
function renderText(raw) {
  if (!raw) return '';
  let html = '';
  const parts = raw.split(/(```[\s\S]*?```)/g);
  parts.forEach(part => {
    if (part.startsWith('```') && part.endsWith('```')) {
      let inner = part.slice(3, -3);
      let lang = '';
      const nl = inner.indexOf('\n');
      if (nl !== -1) {
        const fl = inner.slice(0, nl).trim();
        if (fl && fl.length < 20 && !/\s/.test(fl)) { lang = fl; inner = inner.slice(nl + 1); }
      }
      const codeId = 'c' + Math.random().toString(36).slice(2, 7);
      html += `<div class="code-block-wrap">
        <div class="code-header">
          <span>${esc(lang) || 'code'}</span>
          <button class="copy-btn" onclick="copyCode('${codeId}')">Copy</button>
        </div>
        <pre><code id="${codeId}">${esc(inner.trim())}</code></pre>
      </div>`;
    } else {
      let t = esc(part);
      t = t.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
      t = t.replace(/\n/g, '<br>');
      if (t.trim()) html += '<p>' + t + '</p>';
    }
  });
  return html;
}

function copyCode(id) {
  const el = document.getElementById(id);
  if (!el) return;
  navigator.clipboard.writeText(el.innerText).then(() => {
    const btn = document.querySelector(`[onclick="copyCode('${id}')"]`);
    if (btn) { btn.textContent = '✅ Copied'; setTimeout(() => btn.textContent = 'Copy', 2000); }
  });
}

// ── DOM helpers ──
function removeWelcome() {
  const w = document.getElementById('welcome');
  if (w) w.remove();
}

function scrollBottom() {
  const c = document.getElementById('chat');
  c.scrollTop = c.scrollHeight;
}

function addUserMsg(text) {
  removeWelcome();
  msgCount++;
  if (msgCount === 1) {
    document.getElementById('currentChatLabel').textContent = text.slice(0, 28) + (text.length > 28 ? '…' : '');
  }
  const row = document.createElement('div');
  row.className = 'msg-row user-row';
  row.innerHTML = `
    <div class="avatar user-avatar2">KJ</div>
    <div class="bubble"><p>${esc(text)}</p></div>`;
  document.getElementById('chat').appendChild(row);
  scrollBottom();
}

function addAiMsg(text) {
  const t = document.getElementById('typing');
  if (t) t.remove();
  const row = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `
    <div class="avatar ai-avatar" style="font-size:13px;font-weight:700;">S</div>
    <div class="bubble">${renderText(text || '')}</div>`;
  document.getElementById('chat').appendChild(row);
  scrollBottom();
}

function addTyping() {
  removeWelcome();
  const row = document.createElement('div');
  row.id = 'typing'; row.className = 'msg-row';
  row.innerHTML = `
    <div class="avatar ai-avatar" style="font-size:13px;font-weight:700;">S</div>
    <div class="bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
  document.getElementById('chat').appendChild(row);
  scrollBottom();
}

function addImageMsg(src, label) {
  const t = document.getElementById('typing'); if (t) t.remove();
  const row = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `
    <div class="avatar ai-avatar">✦</div>
    <div class="bubble">
      <div class="img-wrap">
        <img src="${src}" alt="${esc(label || '')}"
          onerror="this.parentElement.innerHTML='<p>❌ Image load nahi hui</p>'">
        <div class="img-label">🖼️ ${esc(label || 'Image')}</div>
      </div>
    </div>`;
  document.getElementById('chat').appendChild(row);
  scrollBottom();
}

// ── Clear / New Chat ──
function buildWelcomeHTML() {
  return `
    <div class="welcome-icon">🤖</div>
    <div class="welcome-title">Sarthi AI</div>
    <div class="welcome-sub">Hindi, English, Hinglish — sab samajhta hun.</div>
    <div class="suggestion-grid">
      <div class="suggestion-card" onclick="suggest('Python mein inheritance kya hota hai?')"><strong>💻 Code Seekhein</strong>Python inheritance explain karo</div>
      <div class="suggestion-card" onclick="suggest('Taj Mahal ki image dikhao')"><strong>🖼️ Image Dekho</strong>Taj Mahal dikhao</div>
      <div class="suggestion-card" onclick="suggest('Aaj ka weather kaisa hai?')"><strong>💬 Baat Karein</strong>Koi bhi sawaal poochho</div>
      <div class="suggestion-card" onclick="suggest('Mujhe motivate karo')"><strong>✨ Motivation</strong>Motivational quote do</div>
    </div>`;
}

function clearChat() {
  msgCount = 0;
  const chat = document.getElementById('chat');
  chat.innerHTML = '';
  const w = document.createElement('div');
  w.id = 'welcome';
  w.innerHTML = buildWelcomeHTML();
  chat.appendChild(w);
  document.getElementById('currentChatLabel').textContent = 'New conversation';
  setStatus('Ready');
  fetch('/clear', { method: 'POST' }).catch(() => {});
}

function newChat() { clearChat(); }

// ── Send ──
async function send() {
  const input = document.getElementById('text');
  const msg = input.value.trim();
  if (!msg) return;

  addUserMsg(msg);
  input.value = '';
  input.style.height = '28px';
  input.style.overflowY = 'hidden';
  addTyping();
  setStatus('⏳ Thinking…');

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();

    // Image response
    if (data.type === 'image') {
      if (data.image_url) addImageMsg(data.image_url, data.query);
      else addAiMsg('❌ Image nahi mili: ' + (data.query || ''));
      setStatus('Ready');
      if (isTalkMode) startListening();
      return;
    }

    const reply = data.reply || '';
    addAiMsg(reply);

    // ── Audio playback ──
    if (data.audio) {
      // ElevenLabs audio available
      if (currentAudio) { currentAudio.pause(); currentAudio = null; }
      cancelSpeech();

      const audio = new Audio('data:audio/mp3;base64,' + data.audio);
      currentAudio = audio;
      setStatus('🔊 Speaking…');

      audio.onended = () => {
        currentAudio = null;
        setStatus('Ready');
        if (isTalkMode) startListening();
      };
      audio.onerror = () => {
        currentAudio = null;
        setStatus('Ready');
        speakText(reply, () => { if (isTalkMode) startListening(); });
      };
      audio.play().catch(() => {
        speakText(reply, () => { if (isTalkMode) startListening(); });
      });

    } else {
      // Fallback: Browser TTS
      speakText(reply, () => { if (isTalkMode) startListening(); });
    }

  } catch(e) {
    const t = document.getElementById('typing'); if (t) t.remove();
    addAiMsg('❌ Error: ' + e.message);
    setStatus('Error');
    if (isTalkMode) startListening();
  }
}

// ── Browser TTS (fallback) ──
function speakText(text, onEnd) {
  // FIXED: Safe guards for undefined/null
  if (!text) { if (onEnd) onEnd(); return; }
  if (!window.speechSynthesis) { if (onEnd) onEnd(); return; }

  cancelSpeech();

  // Clean markdown for speech
  const clean = text
    .replace(/```[\s\S]*?```/g, 'code block.')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/[#*_~]/g, '')
    .trim();

  if (!clean) { if (onEnd) onEnd(); return; }

  // Split into short chunks (Android Chrome bug fix)
  const sentences = clean.match(/[^।!?.]+[।!?.]?/g) || [clean];
  const chunks = [];
  let cur = '';
  sentences.forEach(s => {
    if ((cur + s).length > 180) { if (cur) chunks.push(cur.trim()); cur = s; }
    else cur += s;
  });
  if (cur.trim()) chunks.push(cur.trim());

  const voices = window.speechSynthesis.getVoices();
  let idx = 0;

  // Android Chrome keepAlive fix
  const keepAlive = setInterval(() => {
    if (!window.speechSynthesis || !window.speechSynthesis.speaking) {
      clearInterval(keepAlive); return;
    }
    window.speechSynthesis.pause();
    window.speechSynthesis.resume();
  }, 10000);

  function speakNext() {
    if (idx >= chunks.length) {
      clearInterval(keepAlive);
      setStatus('Ready');
      if (onEnd) onEnd();
      return;
    }
    const utter = new SpeechSynthesisUtterance(chunks[idx++]);
    const isHindi = /[\u0900-\u097F]/.test(utter.text);
    let voice = null;
    if (isHindi) {
      voice = voices.find(v => v.lang.startsWith('hi')) || null;
    } else {
      voice = voices.find(v => v.lang === 'en-IN')
           || voices.find(v => v.lang.startsWith('en-IN'))
           || voices.find(v => v.lang.startsWith('en-US') && v.localService)
           || voices.find(v => v.lang.startsWith('en'))
           || null;
    }
    if (voice) utter.voice = voice;
    utter.lang   = isHindi ? 'hi-IN' : 'en-IN';
    utter.rate   = 0.92; utter.pitch = 1.0; utter.volume = 1.0;
    utter.onend  = speakNext;
    utter.onerror = () => { clearInterval(keepAlive); setStatus('Ready'); if (onEnd) onEnd(); };
    window.speechSynthesis.speak(utter);
  }

  setStatus('🔊 Speaking…');
  speakNext();
}

// Preload voices
if (window.speechSynthesis && window.speechSynthesis.onvoiceschanged !== undefined) {
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}

// ── Mic / Talk Mode ──
function toggleMic() {
  if (isListening) stopListening(); else startListening();
}

function toggleTalk() {
  isTalkMode = !isTalkMode;
  const btn = document.getElementById('talkBtn');
  if (isTalkMode) {
    btn.textContent = '⏹ Stop Talk';
    btn.classList.add('active');
    setStatus('🎙️ Talk Mode ON');
    startListening();
  } else {
    btn.textContent = '🔁 Talk';
    btn.classList.remove('active');
    stopListening();
    cancelSpeech(); // FIXED: safe cancel
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    setStatus('Ready');
  }
}

function buildRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { alert('Chrome use karein mic ke liye!'); return null; }
  const r = new SR();
  r.lang = 'hi-IN'; r.interimResults = false; r.maxAlternatives = 1;
  r.onstart  = () => {
    isListening = true;
    document.getElementById('micBtn').classList.add('active');
    setStatus('🎙️ Listening…');
  };
  r.onresult = (e) => {
    const t = e.results[0][0].transcript;
    document.getElementById('text').value = t;
    stopListening();
    send();
  };
  r.onerror  = (e) => { stopListening(); setStatus('Mic error: ' + e.error); };
  r.onend    = ()  => { stopListening(); };
  return r;
}

function startListening() {
  if (isListening) return;
  cancelSpeech(); // FIXED: safe cancel
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  recognition = buildRecognition();
  if (!recognition) return;
  try { recognition.start(); } catch(e) { console.warn(e); }
}

function stopListening() {
  isListening = false;
  document.getElementById('micBtn').classList.remove('active');
  if (recognition) { try { recognition.stop(); } catch(e) {} recognition = null; }
}
</script>
</body>
</html>
"""


# ================= HELPERS =================

def detect_lang(text):
    hindi = "अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह"
    return "hi" if sum(1 for c in text if c in hindi) > 2 else "en"


def eleven_tts(text):
    """ElevenLabs TTS — returns base64 mp3 or None on failure."""
    try:
        # Clean markdown symbols — baad mein voice mein kharab lagte hain
        clean = re.sub(r'```[\s\S]*?```', 'code block.', text)
        clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
        clean = re.sub(r'`([^`]+)`', r'\1', clean)
        clean = re.sub(r'[#*_~]', '', clean).strip()

        if not clean:
            return None

        audio_generator = eleven.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",       # Rachel — multilingual
            model_id="eleven_multilingual_v2",
            text=clean,
            output_format="mp3_44100_128",
        )

        audio_bytes = b"".join(audio_generator)

        if not audio_bytes:
            print("ElevenLabs: Empty audio received")
            return None

        print(f"ElevenLabs OK — {len(audio_bytes)} bytes")
        return base64.b64encode(audio_bytes).decode()

    except Exception as e:
        print(f"ElevenLabs ERROR: {type(e).__name__}: {e}")
        return None


def web_search(query):
    """Tavily web search — returns answer string or None."""
    if not TAVILY_API_KEY:
        return None
    try:
        payload = json.dumps({
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": 3
        }).encode()
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        if data.get("answer"):
            return data["answer"]
        results = data.get("results", [])
        snippets = [r.get("content", "")[:200] for r in results]
        return " ".join(snippets)
    except Exception as e:
        print("Search error:", e)
        return None


def fetch_image(query):
    """Wikipedia image fetch."""
    try:
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": query,
            "prop": "pageimages", "pithumbsize": 600, "format": "json"
        })
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read().decode())
        for page in data["query"]["pages"].values():
            if "thumbnail" in page:
                return page["thumbnail"]["source"]
    except:
        pass
    return None


# ================= ROUTES =================

@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/clear", methods=["POST"])
def clear():
    global history
    history = []
    return jsonify({"status": "cleared"})


@app.route("/chat", methods=["POST"])
def chat():
    global history
    data = request.json
    msg = data.get("message", "")

    history.append({"role": "user", "content": msg})

    messages = [{"role": "system", "content": SYSTEM}] + history

    # Web search inject
    search = web_search(msg)
    if search:
        messages.insert(1, {
            "role": "system",
            "content": "Latest web info:\n" + search
        })

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=300,
        temperature=0.7
    )

    reply = resp.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    # Image request check
    img_match = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
    if img_match:
        q = img_match.group(1)
        img = fetch_image(q)
        return jsonify({"type": "image", "image_url": img, "query": q})

    # TTS
    audio = eleven_tts(reply)

    return jsonify({"reply": reply, "audio": audio})


# ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
