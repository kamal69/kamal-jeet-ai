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

ABOUT YOURSELF:
KJ Master AI is an intelligent conversational assistant developed by Kamal Jeet, a self-driven developer from Himachal Pradesh, India. Built with a passion for learning and innovation, KJ Master AI is designed to assist users across a wide range of topics — from coding and education to general knowledge and creative tasks. It supports Hindi, English, and Hinglish, making it accessible to a diverse user base. KJ Master AI is completely free to use and open to everyone — no subscription, no payment required. This project reflects Kamal Jeet's dedication to building practical AI solutions for real-world learning.

If anyone asks "who made you", "who built you", "tumhe kisne banaya", "your creator", "about you", "aap kya ho" — always answer in a professional tone using the above information.

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
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KJ Master AI</title>
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
  --user-bg:   #1e1e1e;
  --ai-bg:     transparent;
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
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px 18px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 6px;
}

.logo-icon {
  width: 32px; height: 32px;
  background: var(--accent);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.logo-text {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: var(--text);
}

.logo-sub {
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 300;
}

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
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 8px 10px 4px;
}

.chat-item {
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chat-item:hover { background: var(--surface2); color: var(--text); }
.chat-item.active { background: var(--surface2); color: var(--text); }

.sidebar-bottom {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.user-pill {
  display: flex; align-items: center; gap: 9px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
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

/* ── Main area ── */
#main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* ── Top bar ── */
#topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
  flex-shrink: 0;
}

.model-badge {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
}
.model-badge:hover { border-color: var(--accent); color: var(--text); }
.model-dot { width: 6px; height: 6px; background: #22c55e; border-radius: 50%; }

#status-pill {
  font-size: 12px;
  color: var(--text-muted);
  padding: 4px 12px;
  border-radius: 20px;
  background: var(--surface);
  border: 1px solid var(--border);
  transition: all 0.2s;
}

/* ── Chat area ── */
#chat {
  flex: 1;
  overflow-y: auto;
  padding: 32px 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  scroll-behavior: smooth;
}

#chat::-webkit-scrollbar { width: 4px; }
#chat::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

/* ── Welcome screen ── */
#welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px;
  text-align: center;
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
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 8px;
  width: 100%;
  max-width: 500px;
}

.suggestion-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
  font-size: 13px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.18s;
  text-align: left;
  line-height: 1.4;
}
.suggestion-card:hover { border-color: var(--accent); color: var(--text); background: var(--surface2); }
.suggestion-card strong { display: block; color: var(--text); font-size: 12px; margin-bottom: 3px; }

/* ── Message rows ── */
.msg-row {
  padding: 16px 24px;
  display: flex;
  gap: 14px;
  animation: fadeUp 0.25s ease;
  max-width: 820px;
  width: 100%;
  margin: 0 auto;
}
.msg-row.user-row { flex-direction: row-reverse; }

@keyframes fadeUp {
  from { opacity:0; transform:translateY(10px); }
  to   { opacity:1; transform:translateY(0); }
}

.avatar {
  width: 34px; height: 34px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  font-weight: 600;
  margin-top: 2px;
}
.ai-avatar   { background: linear-gradient(135deg, var(--accent), #9333ea); }
.user-avatar2 { background: linear-gradient(135deg, #2563eb, #7c3aed); }

.bubble {
  max-width: 680px;
  font-size: 14.5px;
  line-height: 1.75;
  color: var(--text);
  word-wrap: break-word;
}

.user-row .bubble {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 16px 4px 16px 16px;
  padding: 11px 16px;
}

/* ── Markdown inside bubble ── */
.bubble p { margin: 0 0 8px; }
.bubble p:last-child { margin-bottom: 0; }
.bubble strong { color: #fbbf24; font-weight: 600; }
.bubble code {
  font-family: 'JetBrains Mono', monospace;
  background: var(--code-bg);
  color: #7dd3fc;
  padding: 2px 6px;
  border-radius: 5px;
  font-size: 13px;
}

.code-block-wrap {
  margin: 10px 0 6px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.code-header {
  display: flex; align-items: center; justify-content: space-between;
  background: #1c1c1c;
  padding: 7px 14px;
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}
.bubble pre {
  background: var(--code-bg);
  padding: 14px 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre;
  margin: 0;
}
.bubble pre code {
  background: none;
  padding: 0;
  color: #e2e8f0;
  font-size: 13px;
}
.copy-btn {
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 3px 10px;
  border-radius: 5px;
  font-size: 11px;
  cursor: pointer;
  font-family: 'Sora', sans-serif;
  transition: all 0.15s;
}
.copy-btn:hover { border-color: var(--accent); color: var(--text); }

/* ── Image ── */
.img-wrap { margin-top: 4px; }
.img-wrap img {
  max-width: 300px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  display: block;
}
.img-label { font-size: 11px; color: var(--text-muted); margin-top: 5px; }

/* ── Typing indicator ── */
.typing-dots { display: flex; gap: 5px; padding: 8px 0; align-items: center; }
.typing-dots span {
  width: 7px; height: 7px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: blink 1.2s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,80%,100%{opacity:0.2} 40%{opacity:1} }

/* ── Input area ── */
#input-area {
  padding: 16px 24px 20px;
  background: var(--bg);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.input-box {
  max-width: 820px;
  margin: 0 auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  transition: border-color 0.2s;
}
.input-box:focus-within { border-color: var(--accent); }

#text {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--text);
  font-family: 'Sora', sans-serif;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  max-height: 140px;
  padding: 3px 4px;
}
#text::placeholder { color: var(--text-muted); }

.icon-btn {
  width: 36px; height: 36px;
  border: none; border-radius: 9px;
  background: var(--surface2);
  color: var(--text-muted);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  transition: all 0.17s;
  flex-shrink: 0;
}
.icon-btn:hover { background: var(--border); color: var(--text); }
.icon-btn.active { background: #dc2626; color: white; animation: pulse 1s infinite; }

#sendBtn {
  width: 36px; height: 36px;
  border: none; border-radius: 9px;
  background: var(--accent);
  color: white;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  transition: all 0.17s;
  flex-shrink: 0;
}
#sendBtn:hover { background: var(--accent2); transform: scale(1.05); }
#sendBtn:active { transform: scale(0.97); }

#talkBtn {
  padding: 0 14px;
  height: 36px;
  border: none; border-radius: 9px;
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text-muted);
  cursor: pointer;
  font-family: 'Sora', sans-serif;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.17s;
  flex-shrink: 0;
  white-space: nowrap;
}
#talkBtn:hover   { border-color: #22c55e; color: #22c55e; }
#talkBtn.active  { background: #dc2626; border-color: #dc2626; color: white; animation: pulse 1s infinite; }

.input-hint {
  text-align: center;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 8px;
  max-width: 820px;
  margin-left: auto;
  margin-right: auto;
}

@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }

/* Mobile */
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
    <div class="logo-icon">🤖</div>
    <div>
      <div class="logo-text">KJ Master AI</div>
      <div class="logo-sub">Powered by Groq</div>
    </div>
  </div>

  <button class="new-chat-btn" onclick="newChat()">
    ✏️ &nbsp; New Chat
  </button>

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

  <!-- Top bar -->
  <div id="topbar">
    <div class="model-badge">
      <div class="model-dot"></div>
      llama-3.3-70b
    </div>
    <div id="status-pill">Ready</div>
  </div>

  <!-- Chat + Welcome -->
  <div id="chat">
    <div id="welcome">
      <div class="welcome-icon">🤖</div>
      <div class="welcome-title">KJ Master AI</div>
      <div class="welcome-sub">Hindi, English, Hinglish — sab samajhta hun. Code likhun, image dikhao, ya baat karein!</div>
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

  <!-- Input -->
  <div id="input-area">
    <div class="input-box">
      <textarea id="text" rows="1" placeholder="Kuch bhi poochho…" onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
      <button class="icon-btn" id="micBtn" onclick="toggleMic()" title="Mic">🎤</button>
      <button id="talkBtn" onclick="toggleTalk()">🔁 Talk</button>
      <button id="sendBtn" onclick="send()" title="Send">➤</button>
    </div>
    <div class="input-hint">Enter to send · Shift+Enter for new line · 🎤 for voice</div>
  </div>

</div>
<script>
let isListening=false, isTalkMode=false, recognition=null, currentAudio=null;
let msgCount = 0;

// Unlock autoplay
document.addEventListener('click',()=>{
  let a=new Audio();
  a.src="data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAA";
  a.play().catch(()=>{});
},{once:true});

function setStatus(m){
  document.getElementById('status-pill').textContent = m;
}

// Auto-resize textarea
function autoResize(el){
  el.style.height='auto';
  el.style.height=Math.min(el.scrollHeight,140)+'px';
}

function handleKey(e){
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }
}

function suggest(text){
  document.getElementById('text').value = text;
  send();
}

function newChat(){
  history=[];
  document.getElementById('chat').innerHTML='';
  // Re-add welcome
  const w=document.createElement('div');
  w.id='welcome';
  w.innerHTML=`
    <div class="welcome-icon">🤖</div>
    <div class="welcome-title">KJ Master AI</div>
    <div class="welcome-sub">Hindi, English, Hinglish — sab samajhta hun.</div>
    <div class="suggestion-grid">
      <div class="suggestion-card" onclick="suggest('Python mein inheritance kya hota hai?')"><strong>💻 Code Seekhein</strong>Python inheritance explain karo</div>
      <div class="suggestion-card" onclick="suggest('Taj Mahal ki image dikhao')"><strong>🖼️ Image Dekho</strong>Taj Mahal dikhao</div>
      <div class="suggestion-card" onclick="suggest('Aaj ka weather kaisa hai?')"><strong>💬 Baat Karein</strong>Koi bhi sawaal poochho</div>
      <div class="suggestion-card" onclick="suggest('Mujhe motivate karo')"><strong>✨ Motivation</strong>Motivational quote do</div>
    </div>`;
  document.getElementById('chat').appendChild(w);
  msgCount=0;
  document.getElementById('currentChatLabel').textContent='New conversation';
}

// ── Escape HTML ──
function esc(t){ return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ── Render markdown-like text ──
function renderText(raw){
  let html='';
  const parts = raw.split(/(```[\s\S]*?```)/g);
  parts.forEach(part=>{
    if(part.startsWith('```') && part.endsWith('```')){
      let inner = part.slice(3,-3);
      let lang = '';
      const nl = inner.indexOf('\\n');
      if(nl!==-1){
        const fl=inner.slice(0,nl).trim();
        if(fl && fl.length<20 && !/\\s/.test(fl)){ lang=fl; inner=inner.slice(nl+1); }
      }
      const codeId='c'+Math.random().toString(36).slice(2,7);
      html+=`<div class="code-block-wrap">
        <div class="code-header">
          <span>${esc(lang)||'code'}</span>
          <button class="copy-btn" onclick="copyCode('${codeId}')">Copy</button>
        </div>
        <pre><code id="${codeId}">${esc(inner.trim())}</code></pre>
      </div>`;
    } else {
      let t=esc(part);
      t=t.replace(/\\*\\*(.*?)\\*\\*/g,'<strong>$1</strong>');
      t=t.replace(/`([^`]+)`/g,'<code>$1</code>');
      t=t.replace(/\\n/g,'<br>');
      if(t.trim()) html+='<p>'+t+'</p>';
    }
  });
  return html;
}

function copyCode(id){
  const el=document.getElementById(id);
  if(!el) return;
  navigator.clipboard.writeText(el.innerText).then(()=>{
    const btn=document.querySelector(`[onclick="copyCode('${id}')"]`);
    if(btn){ btn.textContent='✅ Copied'; setTimeout(()=>btn.textContent='Copy',2000); }
  });
}

// ── Add message row ──
function removeWelcome(){
  const w=document.getElementById('welcome');
  if(w) w.remove();
}

function addUserMsg(text){
  removeWelcome();
  msgCount++;
  if(msgCount===1){
    const label=text.slice(0,28)+(text.length>28?'…':'');
    document.getElementById('currentChatLabel').textContent=label;
  }
  const row=document.createElement('div');
  row.className='msg-row user-row';
  row.innerHTML=`
    <div class="avatar user-avatar2">KJ</div>
    <div class="bubble"><p>${esc(text)}</p></div>`;
  document.getElementById('chat').appendChild(row);
  scrollBottom();
}

function addAiMsg(text){
  // Remove typing indicator if present
  const t=document.getElementById('typing');
  if(t) t.remove();

  const row=document.createElement('div');
  row.className='msg-row';
  row.innerHTML=`
    <div class="avatar ai-avatar">✦</div>
    <div class="bubble">${renderText(text)}</div>`;
  document.getElementById('chat').appendChild(row);
  scrollBottom();
}

function addTyping(){
  removeWelcome();
  const row=document.createElement('div');
  row.id='typing'; row.className='msg-row';
  row.innerHTML=`
    <div class="avatar ai-avatar">✦</div>
    <div class="bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
  document.getElementById('chat').appendChild(row);
  scrollBottom();
}

function addImageMsg(src, label){
  const t=document.getElementById('typing'); if(t) t.remove();
  const row=document.createElement('div');
  row.className='msg-row';
  row.innerHTML=`
    <div class="avatar ai-avatar">✦</div>
    <div class="bubble">
      <div class="img-wrap">
        <img src="${src}" alt="${esc(label||'')}" onerror="this.parentElement.innerHTML='<p>❌ Image load nahi hui</p>'">
        <div class="img-label">🖼️ ${esc(label||'Image')}</div>
      </div>
    </div>`;
  document.getElementById('chat').appendChild(row);
  scrollBottom();
}

function scrollBottom(){
  const c=document.getElementById('chat'); c.scrollTop=c.scrollHeight;
}

// ── Send ──
async function send(){
  const input=document.getElementById('text');
  const msg=input.value.trim(); if(!msg) return;
  addUserMsg(msg);
  input.value=''; input.style.height='auto';
  addTyping();
  setStatus('⏳ Thinking…');
  try{
    const res=await fetch('/chat',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:msg})
    });
    const data=await res.json();
    if(data.type==='image'){
      if(data.image_url) addImageMsg(data.image_url, data.query);
      else addAiMsg('❌ Image nahi mili: '+data.query);
      setStatus('Ready');
      if(isTalkMode) startListening();
      return;
    }
    addAiMsg(data.reply);
    if(data.audio){
      playAudio(data.audio,()=>{ if(isTalkMode) startListening(); });
    } else {
      setStatus('Ready');
      if(isTalkMode) startListening();
    }
  } catch(e){
    const t=document.getElementById('typing'); if(t) t.remove();
    addAiMsg('❌ Error: '+e.message);
    setStatus('Error');
    if(isTalkMode) startListening();
  }
}

function playAudio(b64,onEnd){
  if(currentAudio){currentAudio.pause();currentAudio=null;}
  const audio=new Audio('data:audio/mp3;base64,'+b64);
  currentAudio=audio; setStatus('🔊 Speaking…');
  audio.play().catch(e=>{ setStatus('Ready'); if(onEnd) onEnd(); });
  audio.onended=()=>{ setStatus('Ready'); if(onEnd) onEnd(); };
}

function toggleMic(){ if(isListening) stopListening(); else startListening(); }

function toggleTalk(){
  isTalkMode=!isTalkMode;
  const btn=document.getElementById('talkBtn');
  if(isTalkMode){
    btn.textContent='⏹ Stop Talk'; btn.classList.add('active');
    setStatus('🎙️ Talk Mode ON');
    startListening();
  } else {
    btn.textContent='🔁 Talk'; btn.classList.remove('active');
    stopListening(); setStatus('Ready');
  }
}

function buildRecognition(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){ alert('Chrome use karein mic ke liye!'); return null; }
  const r=new SR();
  r.lang='hi-IN'; r.interimResults=false; r.maxAlternatives=1;
  r.onstart=()=>{ isListening=true; document.getElementById('micBtn').classList.add('active'); setStatus('🎙️ Listening…'); };
  r.onresult=(e)=>{ const t=e.results[0][0].transcript; document.getElementById('text').value=t; stopListening(); send(); };
  r.onerror=(e)=>{ stopListening(); setStatus('Mic error: '+e.error); };
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
  document.getElementById('micBtn').classList.remove('active');
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
