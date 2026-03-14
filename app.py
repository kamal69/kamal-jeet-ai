import os
import base64
import urllib.request
import urllib.parse
import re
import json

from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs

load_dotenv()

app = Flask(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

history = []

SYSTEM = """
You are Sarthi AI - a friendly, smart AI assistant made by Kamal Jeet.
You understand Hindi, English and Hinglish fluently.
Always reply in the same language the user speaks.
Keep replies short and natural for voice conversation.
If user asks for an image, reply ONLY with: [IMAGE:search query]
"""

# HTML is stored as plain bytes — Flask/Jinja2 never processes it
HTML_BYTES = b"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sarthi AI</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0d0d0d; --sidebar:#111; --surface:#1a1a1a; --surface2:#222;
  --border:#2a2a2a; --accent:#c96442; --accent2:#e07a52;
  --text:#ececec; --muted:#888; --code-bg:#161616; --radius:12px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:'Sora',sans-serif;display:flex;height:100vh}

#sidebar{width:240px;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:20px 14px;gap:8px;flex-shrink:0}
.logo{display:flex;align-items:center;gap:10px;padding:8px 10px 18px;border-bottom:1px solid var(--border);margin-bottom:6px}
.logo-text{font-size:15px;font-weight:600}
.logo-sub{font-size:10px;color:var(--muted)}
.new-btn{display:flex;align-items:center;gap:8px;padding:9px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);color:var(--text);font-family:'Sora',sans-serif;font-size:13px;cursor:pointer;width:100%;text-align:left;transition:all .18s}
.new-btn:hover{background:var(--surface);border-color:var(--accent)}
.sidebar-label{font-size:10px;font-weight:500;color:var(--muted);text-transform:uppercase;letter-spacing:1px;padding:8px 10px 4px}
.chat-item{padding:8px 10px;border-radius:8px;font-size:12.5px;color:var(--muted);cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chat-item.active{background:var(--surface2);color:var(--text)}
.sidebar-footer{margin-top:auto;padding-top:12px;border-top:1px solid var(--border)}
.user-pill{display:flex;align-items:center;gap:9px;padding:8px 10px;border-radius:8px;cursor:pointer}
.user-pill:hover{background:var(--surface2)}
.uavatar{width:28px;height:28px;background:linear-gradient(135deg,var(--accent),#7c3aed);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;flex-shrink:0}

#main{flex:1;display:flex;flex-direction:column;overflow:hidden}
#topbar{display:flex;align-items:center;justify-content:space-between;padding:14px 24px;border-bottom:1px solid var(--border);flex-shrink:0}
.badge{display:flex;align-items:center;gap:6px;padding:5px 12px;background:var(--surface);border:1px solid var(--border);border-radius:20px;font-size:12px;color:var(--muted)}
.dot{width:6px;height:6px;background:#22c55e;border-radius:50%}
#status{font-size:12px;color:var(--muted);padding:4px 12px;border-radius:20px;background:var(--surface);border:1px solid var(--border)}
.clear-btn{background:none;border:1px solid var(--border);color:var(--muted);padding:5px 12px;border-radius:20px;cursor:pointer;font-size:12px;font-family:'Sora',sans-serif}
.clear-btn:hover{border-color:#ef4444;color:#ef4444}

#chat{flex:1;overflow-y:auto;padding:32px 0;display:flex;flex-direction:column;scroll-behavior:smooth}
#chat::-webkit-scrollbar{width:4px}
#chat::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px}

#welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:40px;text-align:center;min-height:100%}
.welcome-icon{width:56px;height:56px;background:linear-gradient(135deg,var(--accent),#9333ea);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:28px;box-shadow:0 0 40px rgba(201,100,66,.25)}
.welcome-title{font-size:26px;font-weight:600}
.welcome-sub{font-size:14px;color:var(--muted);max-width:360px;line-height:1.6}
.sgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px;width:100%;max-width:500px}
.scard{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:12px 14px;font-size:13px;color:var(--muted);cursor:pointer;text-align:left;line-height:1.4;transition:all .18s}
.scard:hover{border-color:var(--accent);color:var(--text);background:var(--surface2)}
.scard strong{display:block;color:var(--text);font-size:12px;margin-bottom:3px}

.row{padding:16px 24px;display:flex;gap:14px;max-width:820px;width:100%;margin:0 auto;animation:fadeUp .25s ease}
.row.user{flex-direction:row-reverse}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.av{width:34px;height:34px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;margin-top:2px}
.av.ai{background:linear-gradient(135deg,var(--accent),#9333ea)}
.av.user{background:linear-gradient(135deg,#2563eb,#7c3aed)}
.bubble{max-width:680px;font-size:14.5px;line-height:1.75;color:var(--text);word-wrap:break-word}
.row.user .bubble{background:var(--surface2);border:1px solid var(--border);border-radius:16px 4px 16px 16px;padding:11px 16px}
.bubble p{margin:0 0 8px}
.bubble p:last-child{margin-bottom:0}
.bubble strong{color:#fbbf24}
.bubble code{font-family:'JetBrains Mono',monospace;background:var(--code-bg);color:#7dd3fc;padding:2px 6px;border-radius:5px;font-size:13px}
.code-wrap{margin:10px 0;border-radius:10px;overflow:hidden;border:1px solid var(--border)}
.code-head{display:flex;align-items:center;justify-content:space-between;background:#1c1c1c;padding:7px 14px;font-size:11px;color:var(--muted);font-family:'JetBrains Mono',monospace}
.bubble pre{background:var(--code-bg);padding:14px 16px;overflow-x:auto;margin:0}
.bubble pre code{background:none;padding:0;color:#e2e8f0}
.copy-btn{background:var(--surface2);border:1px solid var(--border);color:var(--muted);padding:3px 10px;border-radius:5px;font-size:11px;cursor:pointer;font-family:'Sora',sans-serif}
.copy-btn:hover{border-color:var(--accent);color:var(--text)}
.img-wrap img{max-width:300px;border-radius:var(--radius);border:1px solid var(--border);display:block}
.img-label{font-size:11px;color:var(--muted);margin-top:5px}

.typing{display:flex;gap:5px;padding:8px 0;align-items:center}
.typing span{width:7px;height:7px;background:var(--muted);border-radius:50%;animation:blink 1.2s infinite}
.typing span:nth-child(2){animation-delay:.2s}
.typing span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}

#input-wrap{padding:16px 24px 20px;border-top:1px solid var(--border);flex-shrink:0}
.input-box{max-width:820px;margin:0 auto;background:var(--surface);border:1px solid var(--border);border-radius:14px;display:flex;align-items:flex-end;gap:8px;padding:10px 12px;transition:border-color .2s}
.input-box:focus-within{border-color:var(--accent)}
#textInput{flex:1;background:none;border:none;outline:none;color:var(--text);font-family:'Sora',sans-serif;font-size:14px;line-height:1.5;resize:none;padding:3px 4px;height:26px;min-height:26px;max-height:140px;overflow-y:hidden}
#textInput::placeholder{color:var(--muted)}
.ibtn{width:36px;height:36px;border:none;border-radius:9px;background:var(--surface2);color:var(--muted);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;transition:all .17s;flex-shrink:0}
.ibtn:hover{background:var(--border);color:var(--text)}
.ibtn.on{background:#dc2626;color:white}
#talkBtn{padding:0 14px;height:36px;border-radius:9px;background:var(--surface2);border:1px solid var(--border);color:var(--muted);cursor:pointer;font-family:'Sora',sans-serif;font-size:12px;font-weight:500;transition:all .17s;flex-shrink:0;white-space:nowrap}
#talkBtn:hover{border-color:#22c55e;color:#22c55e}
#talkBtn.on{background:#dc2626;border-color:#dc2626;color:white}
#sendBtn{width:36px;height:36px;border:none;border-radius:9px;background:var(--accent);color:white;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;transition:all .17s;flex-shrink:0}
#sendBtn:hover{background:var(--accent2);transform:scale(1.05)}
.hint{text-align:center;font-size:11px;color:var(--muted);margin-top:8px}

@media(max-width:640px){#sidebar{display:none}.row{padding:12px 14px}#input-wrap{padding:12px 14px 16px}}
</style>
</head>
<body>

<div id="sidebar">
  <div class="logo">
    <svg width="32" height="32" viewBox="0 0 36 36">
      <rect width="36" height="36" rx="10" fill="#1a1a1a" stroke="#2a2a2a" stroke-width="1"/>
      <circle cx="18" cy="18" r="10" fill="none" stroke="#c96442" stroke-width="1.5"/>
      <circle cx="18" cy="18" r="6" fill="#c96442" opacity="0.15"/>
      <polygon points="18,8 20,14 18,12 16,14" fill="#c96442"/>
      <circle cx="18" cy="18" r="2.5" fill="#c96442"/>
    </svg>
    <div>
      <div class="logo-text">Sarthi AI</div>
      <div class="logo-sub">Powered by Kamal Jeet</div>
    </div>
  </div>
  <button class="new-btn" id="newChatBtn">&#9997;&#160; New Chat</button>
  <div class="sidebar-label">Recent</div>
  <div class="chat-item active" id="chatLabel">New conversation</div>
  <div class="sidebar-footer">
    <div class="user-pill">
      <div class="uavatar">KJ</div>
      <div>
        <div style="font-size:12.5px;font-weight:500">Kamal Jeet</div>
        <div style="font-size:11px;color:var(--muted)">Himachal Pradesh</div>
      </div>
    </div>
  </div>
</div>

<div id="main">
  <div id="topbar">
    <div class="badge"><div class="dot"></div> Online</div>
    <div style="display:flex;gap:10px;align-items:center">
      <button class="clear-btn" id="clearBtn">&#128465; Clear</button>
      <div id="status">Ready</div>
    </div>
  </div>

  <div id="chat">
    <div id="welcome">
      <div class="welcome-icon">&#129302;</div>
      <div class="welcome-title">Sarthi AI</div>
      <div class="welcome-sub">Hindi, English, Hinglish &mdash; sab samajhta hun.</div>
      <div class="sgrid">
        <div class="scard" data-q="Python mein inheritance kya hota hai?"><strong>&#128187; Code</strong>Python inheritance explain karo</div>
        <div class="scard" data-q="Taj Mahal ki image dikhao"><strong>&#128444; Image</strong>Taj Mahal dikhao</div>
        <div class="scard" data-q="Aaj ka weather kaisa hai?"><strong>&#128172; Baat</strong>Koi bhi sawaal poochho</div>
        <div class="scard" data-q="Mujhe motivate karo"><strong>&#10024; Motivation</strong>Motivational quote do</div>
      </div>
    </div>
  </div>

  <div id="input-wrap">
    <div class="input-box">
      <textarea id="textInput" placeholder="Kuch bhi poochho..."></textarea>
      <button class="ibtn" id="micBtn" title="Mic">&#127908;</button>
      <button id="talkBtn">&#128257; Talk</button>
      <button id="sendBtn">&#9658;</button>
    </div>
    <div class="hint">Enter = send &nbsp;&middot;&nbsp; Shift+Enter = new line</div>
  </div>
</div>

<script>
var isListening = false;
var isTalkMode  = false;
var recognition = null;
var currentAudio = null;
var msgCount = 0;

var textInput  = document.getElementById('textInput');
var sendBtn    = document.getElementById('sendBtn');
var micBtn     = document.getElementById('micBtn');
var talkBtn    = document.getElementById('talkBtn');
var clearBtn   = document.getElementById('clearBtn');
var newChatBtn = document.getElementById('newChatBtn');
var chatEl     = document.getElementById('chat');

// Suggestion cards
chatEl.addEventListener('click', function(e) {
  var card = e.target.closest('.scard');
  if (card) { textInput.value = card.getAttribute('data-q'); doSend(); return; }
  var cb = e.target.closest('.copy-btn');
  if (cb) {
    var el = document.getElementById(cb.getAttribute('data-id'));
    if (el) navigator.clipboard.writeText(el.innerText).then(function() {
      cb.textContent = 'Copied!';
      setTimeout(function() { cb.textContent = 'Copy'; }, 2000);
    });
  }
});

// Textarea auto-resize
textInput.addEventListener('input', function() {
  this.style.height = '26px';
  var sh = this.scrollHeight;
  this.style.height = (sh > 140 ? 140 : sh) + 'px';
  this.style.overflowY = sh > 140 ? 'auto' : 'hidden';
});

// Enter to send
textInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(); }
});

sendBtn.addEventListener('click',    function() { doSend(); });
clearBtn.addEventListener('click',   function() { doClear(); });
newChatBtn.addEventListener('click', function() { doClear(); });
micBtn.addEventListener('click',     function() { if (isListening) stopListen(); else startListen(); });
talkBtn.addEventListener('click',    function() { doToggleTalk(); });

// Unlock audio autoplay
document.addEventListener('click', function() {
  var a = new Audio();
  a.src = 'data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAA';
  a.play().catch(function(){});
}, { once: true });

function setStatus(m) { document.getElementById('status').textContent = m; }

function safeCancel() {
  try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch(e) {}
}

function esc(t) {
  return (t || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderMD(raw) {
  if (!raw) return '';
  var html = '';
  var parts = raw.split(/(```[\s\S]*?```)/g);
  for (var i = 0; i < parts.length; i++) {
    var part = parts[i];
    if (part.slice(0,3) === '```' && part.slice(-3) === '```') {
      var inner = part.slice(3, -3);
      var lang = '';
      var nl = inner.indexOf('\\n');
      if (nl !== -1) {
        var fl = inner.slice(0, nl).trim();
        if (fl && fl.length < 20 && fl.indexOf(' ') === -1) { lang = fl; inner = inner.slice(nl + 1); }
      }
      var cid = 'c' + Math.random().toString(36).slice(2,7);
      html += '<div class="code-wrap"><div class="code-head"><span>' + esc(lang||'code') + '</span>'
            + '<button class="copy-btn" data-id="' + cid + '">Copy</button></div>'
            + '<pre><code id="' + cid + '">' + esc(inner.trim()) + '</code></pre></div>';
    } else {
      var t = esc(part);
      t = t.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
      t = t.replace(/\n/g, '<br>');
      if (t.trim()) html += '<p>' + t + '</p>';
    }
  }
  return html;
}

function scrollDown() { chatEl.scrollTop = chatEl.scrollHeight; }

function removeWelcome() { var w = document.getElementById('welcome'); if (w) w.remove(); }

function addUserMsg(text) {
  removeWelcome();
  msgCount++;
  if (msgCount === 1) {
    document.getElementById('chatLabel').textContent = text.slice(0,28) + (text.length > 28 ? '...' : '');
  }
  var row = document.createElement('div');
  row.className = 'row user';
  row.innerHTML = '<div class="av user">KJ</div><div class="bubble"><p>' + esc(text) + '</p></div>';
  chatEl.appendChild(row);
  scrollDown();
}

function addAiMsg(text) {
  var t = document.getElementById('typingRow'); if (t) t.remove();
  var row = document.createElement('div');
  row.className = 'row';
  row.innerHTML = '<div class="av ai">S</div><div class="bubble">' + renderMD(text||'') + '</div>';
  chatEl.appendChild(row);
  scrollDown();
}

function addTyping() {
  removeWelcome();
  var row = document.createElement('div');
  row.className = 'row'; row.id = 'typingRow';
  row.innerHTML = '<div class="av ai">S</div><div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
  chatEl.appendChild(row);
  scrollDown();
}

function addImageMsg(src, label) {
  var t = document.getElementById('typingRow'); if (t) t.remove();
  var row = document.createElement('div');
  row.className = 'row';
  row.innerHTML = '<div class="av ai">S</div><div class="bubble"><div class="img-wrap">'
    + '<img src="' + src + '" onerror="this.parentElement.innerHTML=\'Image load nahi hui\'">'
    + '<div class="img-label">' + esc(label||'Image') + '</div></div></div>';
  chatEl.appendChild(row);
  scrollDown();
}

function makeWelcomeHTML() {
  return '<div class="welcome-icon">&#129302;</div>'
    + '<div class="welcome-title">Sarthi AI</div>'
    + '<div class="welcome-sub">Hindi, English, Hinglish &mdash; sab samajhta hun.</div>'
    + '<div class="sgrid">'
    + '<div class="scard" data-q="Python mein inheritance kya hota hai?"><strong>&#128187; Code</strong>Python inheritance explain karo</div>'
    + '<div class="scard" data-q="Taj Mahal ki image dikhao"><strong>&#128444; Image</strong>Taj Mahal dikhao</div>'
    + '<div class="scard" data-q="Aaj ka weather kaisa hai?"><strong>&#128172; Baat</strong>Koi bhi sawaal poochho</div>'
    + '<div class="scard" data-q="Mujhe motivate karo"><strong>&#10024; Motivation</strong>Motivational quote do</div>'
    + '</div>';
}

function doClear() {
  msgCount = 0;
  chatEl.innerHTML = '';
  var w = document.createElement('div');
  w.id = 'welcome'; w.innerHTML = makeWelcomeHTML();
  chatEl.appendChild(w);
  document.getElementById('chatLabel').textContent = 'New conversation';
  setStatus('Ready');
  fetch('/clear', { method: 'POST' }).catch(function(){});
}

function doSend() {
  var msg = textInput.value.trim();
  if (!msg) return;
  addUserMsg(msg);
  textInput.value = '';
  textInput.style.height = '26px';
  textInput.style.overflowY = 'hidden';
  addTyping();
  setStatus('Thinking...');

  fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg })
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    if (data.type === 'image') {
      if (data.image_url) addImageMsg(data.image_url, data.query||'');
      else addAiMsg('Image nahi mili: ' + (data.query||''));
      setStatus('Ready');
      if (isTalkMode) startListen();
      return;
    }
    var reply = data.reply || '';
    addAiMsg(reply);
    if (data.audio) {
      if (currentAudio) { currentAudio.pause(); currentAudio = null; }
      safeCancel();
      var audio = new Audio('data:audio/mp3;base64,' + data.audio);
      currentAudio = audio;
      setStatus('Speaking...');
      audio.onended = function() { currentAudio = null; setStatus('Ready'); if (isTalkMode) startListen(); };
      audio.onerror = function() { currentAudio = null; speakText(reply, function() { if (isTalkMode) startListen(); }); };
      audio.play().catch(function() { speakText(reply, function() { if (isTalkMode) startListen(); }); });
    } else {
      speakText(reply, function() { if (isTalkMode) startListen(); });
    }
  })
  .catch(function(e) {
    var t = document.getElementById('typingRow'); if (t) t.remove();
    addAiMsg('Error: ' + e.message);
    setStatus('Error');
    if (isTalkMode) startListen();
  });
}

function speakText(text, onEnd) {
  if (!text) { if (onEnd) onEnd(); return; }
  if (!window.speechSynthesis) { if (onEnd) onEnd(); return; }
  safeCancel();
  var clean = text
    .replace(/```[\s\S]*?```/g, 'code block.')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/[#*_~]/g, '').trim();
  if (!clean) { if (onEnd) onEnd(); return; }
  var sentences = clean.match(/[^\u0964!?.]+[\u0964!?.]?/g) || [clean];
  var chunks = []; var cur = '';
  for (var i = 0; i < sentences.length; i++) {
    var s = sentences[i];
    if ((cur + s).length > 180) { if (cur) chunks.push(cur.trim()); cur = s; }
    else cur += s;
  }
  if (cur.trim()) chunks.push(cur.trim());
  var voices = window.speechSynthesis.getVoices();
  var idx = 0;
  var ka = setInterval(function() {
    if (!window.speechSynthesis || !window.speechSynthesis.speaking) { clearInterval(ka); return; }
    window.speechSynthesis.pause(); window.speechSynthesis.resume();
  }, 10000);
  function next() {
    if (idx >= chunks.length) { clearInterval(ka); setStatus('Ready'); if (onEnd) onEnd(); return; }
    var u = new SpeechSynthesisUtterance(chunks[idx++]);
    var isH = /[\u0900-\u097F]/.test(u.text);
    var v = null;
    if (isH) { for (var i=0;i<voices.length;i++) { if (voices[i].lang.indexOf('hi')===0){v=voices[i];break;} } }
    else { for (var i=0;i<voices.length;i++) { if (voices[i].lang==='en-IN'){v=voices[i];break;} } }
    if (!v) { for (var i=0;i<voices.length;i++) { if (voices[i].lang.indexOf('en')===0){v=voices[i];break;} } }
    if (v) u.voice = v;
    u.lang = isH ? 'hi-IN' : 'en-IN';
    u.rate = 0.92; u.pitch = 1.0; u.volume = 1.0;
    u.onend = next;
    u.onerror = function() { clearInterval(ka); setStatus('Ready'); if (onEnd) onEnd(); };
    window.speechSynthesis.speak(u);
  }
  setStatus('Speaking...');
  next();
}

if (window.speechSynthesis && window.speechSynthesis.onvoiceschanged !== undefined) {
  window.speechSynthesis.onvoiceschanged = function() { window.speechSynthesis.getVoices(); };
}

function doToggleTalk() {
  isTalkMode = !isTalkMode;
  if (isTalkMode) {
    talkBtn.textContent = 'Stop'; talkBtn.classList.add('on');
    setStatus('Talk Mode ON'); startListen();
  } else {
    talkBtn.textContent = 'Talk'; talkBtn.classList.remove('on');
    stopListen(); safeCancel();
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    setStatus('Ready');
  }
}

function buildRec() {
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { alert('Chrome use karein mic ke liye!'); return null; }
  var r = new SR();
  r.lang = 'hi-IN'; r.interimResults = false; r.maxAlternatives = 1;
  r.onstart = function() { isListening = true; micBtn.classList.add('on'); setStatus('Listening...'); };
  r.onresult = function(e) { textInput.value = e.results[0][0].transcript; stopListen(); doSend(); };
  r.onerror = function(e) { stopListen(); setStatus('Mic error: ' + e.error); };
  r.onend   = function() { stopListen(); };
  return r;
}

function startListen() {
  if (isListening) return;
  safeCancel();
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  recognition = buildRec(); if (!recognition) return;
  try { recognition.start(); } catch(e) { console.warn(e); }
}

function stopListen() {
  isListening = false; micBtn.classList.remove('on');
  if (recognition) { try { recognition.stop(); } catch(e) {} recognition = null; }
}
</script>
</body>
</html>"""


# ── Routes ──────────────────────────────────────────

@app.route("/")
def home():
    # Serve raw bytes — Jinja2 never sees this HTML
    return Response(HTML_BYTES, mimetype="text/html")


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

    search_result = web_search(msg)
    if search_result:
        messages.insert(1, {"role": "system", "content": "Latest web info:\n" + search_result})

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=300,
        temperature=0.7
    )

    reply = resp.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    img_match = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
    if img_match:
        q = img_match.group(1)
        img = fetch_image(q)
        return jsonify({"type": "image", "image_url": img, "query": q})

    audio = eleven_tts(reply)
    return jsonify({"reply": reply, "audio": audio})


# ── Helpers ─────────────────────────────────────────

def eleven_tts(text):
    try:
        clean = re.sub(r'```[\s\S]*?```', 'code block.', text)
        clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
        clean = re.sub(r'`([^`]+)`', r'\1', clean)
        clean = re.sub(r'[#*_~]', '', clean).strip()
        if not clean:
            return None
        audio_gen = eleven.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            model_id="eleven_multilingual_v2",
            text=clean,
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_gen)
        if not audio_bytes:
            return None
        print("ElevenLabs OK -- " + str(len(audio_bytes)) + " bytes")
        return base64.b64encode(audio_bytes).decode()
    except Exception as e:
        print("ElevenLabs ERROR: " + str(e))
        return None


def web_search(query):
    if not TAVILY_API_KEY:
        return None
    try:
        payload = json.dumps({"api_key": TAVILY_API_KEY, "query": query, "max_results": 3}).encode()
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
        return " ".join([x.get("content", "")[:200] for x in data.get("results", [])])
    except Exception as e:
        print("Search error: " + str(e))
        return None


def fetch_image(query):
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
