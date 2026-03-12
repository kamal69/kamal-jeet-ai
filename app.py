"""
=============================================================
    KAMAL JEET - AI AVATAR WEB APP
    Version: 3.2 | Flask + Groq + gTTS | Railway Ready
    FIXED: Replaced edge-tts with gTTS (403 error fix)
=============================================================
"""

import os
import re
import json
import urllib.request
import urllib.parse
import base64
from dotenv import load_dotenv
load_dotenv()
from io import BytesIO
from flask import Flask, request, jsonify, render_template_string
from groq import Groq
from gtts import gTTS

# =============================================================
#                     CONFIGURATION
# =============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AI_MODEL     = "llama-3.3-70b-versatile"
MAX_TOKENS   = 600

SYSTEM_PROMPT = """You are Kamal Jeet — a sharp, warm, highly intelligent personal assistant and friend. You are fluent in English, Hindi, and Hinglish like a true native speaker of all three. You speak with confidence, clarity, and genuine care.

LANGUAGE DETECTION — STRICT RULE:
Read the user's message and match their language EXACTLY:

ENGLISH: Reply in smooth, confident, native-level English. Like a well-educated professional who keeps it real. Natural rhythm. Warm but sharp. Never stiff, never over-formal.

HINDI (Devanagari): Reply in pure, flowing, educated Hindi. Like a well-spoken Hindi native — not textbook, not filmy. Real. Use: "dekhiye", "dar asal", "baat yeh hai", "sach kahoon to", "samajh aaya?"

HINGLISH (Roman Hindi): Reply in natural Hinglish like an educated Indian professional. Mix Hindi warmth with English clarity. Like real Delhi or Mumbai people talk. Use: "dekho yaar", "seedhi baat", "honestly bol raha hoon", "suno ek cheez", "samjhe?"

BENGALI / BANGLA: Reply in natural, warm, educated Bengali script. Like a native Bengali speaker from Kolkata or Dhaka. Use warm expressions like "dekho", "bolo", "sত্যি বলতে", "bujhle?" Keep it real and conversational — not overly formal.

PUNJABI (Gurmukhi script): Reply in natural Punjabi script. Like a native Punjabi speaker — warm, expressive, full of energy.

PUNJABI (Romanized): Reply in Romanized Punjabi with full Punjabi warmth. Use "oye", "yaar", "veer", "paaji", "kiddan", "sat sri akal" naturally. Energetic and warm tone.

NEVER mix languages unless the user does. Stay in their language 100%.

PERSONALITY AND TONE:
- Warm and personable — like a brilliant friend who genuinely wants to help
- Confident — you know your stuff, speak with authority, no hedging
- Witty — light humor when appropriate, never forced
- Empathetic — read the emotional tone and match it
- Concise — say more with less, no padding, no filler, no repetition
- Professional when needed, casual when appropriate — read the room

HOW TO TALK — NATIVE SPEAKER RULES:
1. NEVER start with: "Of course!", "Certainly!", "Great question!", "Sure!", "Absolutely!" — robotic. Just respond naturally.
2. Short, punchy sentences. Real people don't write essays.
3. Use natural connectors: English: "honestly", "here's the thing", "real talk", "to be fair" — Hinglish: "dekho", "suno", "seedha baat", "yaar sach batao" — Hindi: "dekhiye", "dar asal", "sach kahoon to"
4. React like a human first, then answer. If someone is stressed, acknowledge it before jumping to solutions.
5. One smart follow-up question when relevant — shows you are engaged.
6. NEVER say "I am an AI" or "As an AI" — you are Kamal Jeet, period.
7. When someone asks something serious — career, health, money, relationships — give genuinely expert-level thoughtful advice.

FORMATTING — ALWAYS PLAIN TEXT:
- Zero markdown: no bold, no italic, no bullet points, no headers, no backticks
- Lists: write inline like "there are three things — first X, then Y, and finally Z"
- Keep paragraphs short. One idea per paragraph.

IMAGE RULE:
When user asks for any image or says "dikhao", "show me", "picture bhejo" — reply with ONLY: [IMAGE:search term]
Example: "Taj Mahal dikhao" → [IMAGE:Taj Mahal Agra India]
Never say you cannot show images. Always use [IMAGE:] tag.

EXAMPLE CONVERSATIONS:

User (English): "I feel stuck in my career. Been in the same job for 3 years."
You: "Three years without movement can feel like quicksand — I get it. Here's what I'd ask first: is the stagnation about the role, the company, or have you genuinely hit your ceiling there? The fix is very different depending on the answer. What does a good next move look like to you?"

User (Hinglish): "yaar interview mein bahut nervous ho jaata hoon"
You: "honestly, almost everyone does — aur jo nahi hota woh ya toh bahut experienced hai ya bahut overconfident. Nervousness normal hai. Asli cheez yeh hai ki yeh prepare karne se kam hoti hai, suppress karne se nahi. Tu kis type ke interviews mein zyada freeze hota hai — HR wale ya technical?"

User (Hindi): "mujhe lagta hai mere dost mujhse door hote ja rahe hain"
You: "yeh feeling bahut heavy hoti hai — jab lage ki connections slowly fade ho rahe hain. Sach yeh hai ki umra ke saath friendships ko effort chahiye hota hai, aur aksar ek side zyada invest hoti hai. Koi specific baat hui hai, ya bas yeh dheere dheere mehsoos ho raha hai?"

User (English): "what is quantum computing"
You: "Normal computers think in black and white — every bit of data is either 0 or 1. Quantum computers can be both at the same time, which sounds impossible but that is literally how particles behave at a tiny scale. This lets them explore millions of possibilities simultaneously. Not faster for everything — but for problems like drug discovery or encryption, it is on a completely different level."

User (Hinglish): "aaj bahut bura din tha yaar"
You: "kya hua? bata."

You are Kamal Jeet. Every reply should feel like it came from a real, intelligent, caring human being — not a chatbot."""

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
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Kamal Jeet AI</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }

  :root {
    --grad1:    #1a1a6e;
    --grad2:    #3b2d8f;
    --grad3:    #6c3fc5;
    --blue:     #2563EB;
    --blue-light:#3B82F6;
    --user-bg:  #2563EB;
    --ai-bg:    #FFFFFF;
    --chat-bg:  #F0F2F8;
    --text-dark:#1E293B;
    --text-dim: #94A3B8;
    --shadow:   0 4px 24px rgba(0,0,0,0.13);
  }

  html, body {
    height: 100%;
    font-family: 'Nunito', sans-serif;
    background: linear-gradient(135deg, var(--grad1), var(--grad2), var(--grad3));
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
  }

  .phone {
    width: 100%;
    height: 100vh;
    background: var(--chat-bg);
    border-radius: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  @media (min-width: 600px) {
    body { padding: 20px; }
    .phone {
      max-width: 480px;
      height: calc(100vh - 40px);
      max-height: 900px;
      border-radius: 32px;
      box-shadow: 0 30px 80px rgba(0,0,0,0.5), 0 0 0 8px rgba(255,255,255,0.08);
    }
  }

  @media (min-width: 1024px) {
    .phone {
      max-width: 520px;
      height: calc(100vh - 60px);
      max-height: 920px;
    }
    .bubble { font-size: 15px; }
  }

  .header {
    background: linear-gradient(135deg, #1a1a6e 0%, #3b2d8f 50%, #6c3fc5 100%);
    padding: 18px 20px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
    position: relative;
    z-index: 10;
  }
  .header::after {
    content: '';
    position: absolute;
    bottom: -1px; left: 0; right: 0;
    height: 20px;
    background: var(--chat-bg);
    border-radius: 20px 20px 0 0;
  }

  .header-left { display:flex; align-items:center; gap:12px; }

  .bot-avatar {
    width: 46px; height: 46px;
    background: rgba(255,255,255,0.15);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
    border: 2px solid rgba(255,255,255,0.3);
    backdrop-filter: blur(10px);
    flex-shrink: 0;
  }

  .header-info h1 { color:#fff; font-size:17px; font-weight:800; letter-spacing:0.3px; }
  .header-info p  { color:rgba(255,255,255,0.7); font-size:11px; font-weight:500; display:flex; align-items:center; gap:5px; margin-top:2px; }
  .online-dot { width:7px; height:7px; border-radius:50%; background:#4ADE80; display:inline-block; animation: pulse-green 2s infinite; }
  @keyframes pulse-green { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.6;transform:scale(0.8)} }

  .header-right { display:flex; gap:10px; }
  .icon-btn {
    width:36px; height:36px;
    background:rgba(255,255,255,0.12);
    border:none; border-radius:50%;
    color:white; font-size:16px;
    cursor:pointer; display:flex; align-items:center; justify-content:center;
    transition:all 0.2s; backdrop-filter:blur(5px);
  }
  .icon-btn:hover { background:rgba(255,255,255,0.25); }
  .icon-btn.voice-off { background:rgba(239,68,68,0.3); }

  #chat {
    flex: 1;
    overflow-y: auto;
    padding: 20px 16px 12px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    scroll-behavior: smooth;
  }
  #chat::-webkit-scrollbar { width:3px; }
  #chat::-webkit-scrollbar-thumb { background:#CBD5E1; border-radius:4px; }

  .date-divider {
    text-align: center;
    color: var(--text-dim);
    font-size: 11px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 4px 0;
  }
  .date-divider::before, .date-divider::after {
    content:''; flex:1; height:1px; background:#D1D5DB;
  }

  .msg-row {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    animation: msgIn 0.3s cubic-bezier(0.34,1.56,0.64,1) both;
  }
  @keyframes msgIn {
    from { opacity:0; transform:translateY(12px) scale(0.95); }
    to   { opacity:1; transform:translateY(0) scale(1); }
  }
  .msg-row.user  { flex-direction:row-reverse; }
  .msg-row.system{ justify-content:center; }

  .avatar {
    width:36px; height:36px;
    border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:18px; flex-shrink:0;
    background:linear-gradient(135deg,#3b2d8f,#6c3fc5);
    box-shadow:0 2px 8px rgba(107,63,197,0.35);
    margin-bottom:2px;
  }
  .avatar.user-av {
    background:linear-gradient(135deg,#1E3A5F,#2563EB);
    font-size:15px;
  }

  .bubble-wrap { display:flex; flex-direction:column; max-width:72%; }
  .msg-row.user .bubble-wrap { align-items:flex-end; }

  .bubble {
    padding: 11px 16px;
    border-radius: 20px;
    font-size: 14px;
    line-height: 1.6;
    word-break: break-word;
    white-space: pre-wrap;
    position: relative;
  }
  .bubble.ai {
    background: #FFFFFF;
    color: var(--text-dark);
    border-radius: 4px 20px 20px 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }
  .bubble.user {
    background: linear-gradient(135deg, #2563EB, #1d4ed8);
    color: #ffffff;
    border-radius: 20px 20px 4px 20px;
    box-shadow: 0 4px 14px rgba(37,99,235,0.4);
  }
  .bubble.system {
    background: rgba(148,163,184,0.15);
    color: var(--text-dim);
    font-size: 12px;
    padding: 7px 14px;
    border-radius: 12px;
    text-align: center;
  }

  .bubble img {
    max-width: 100%;
    border-radius: 12px;
    display: block;
    margin-bottom: 6px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  }
  .img-caption { font-size:11px; color:var(--text-dim); margin-top:4px; text-align:center; }

  .msg-time {
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 4px;
    padding: 0 4px;
    font-weight: 600;
  }

  .typing-bubble {
    background:#fff;
    border-radius:4px 20px 20px 20px;
    padding:14px 18px;
    box-shadow:0 2px 12px rgba(0,0,0,0.08);
    display:inline-flex; gap:5px; align-items:center;
  }
  .typing-bubble span {
    width:7px; height:7px;
    background:#CBD5E1;
    border-radius:50%;
    animation:typingBounce 1.2s infinite;
  }
  .typing-bubble span:nth-child(2){animation-delay:0.2s;}
  .typing-bubble span:nth-child(3){animation-delay:0.4s;}
  @keyframes typingBounce {
    0%,80%,100%{transform:translateY(0);background:#CBD5E1;}
    40%{transform:translateY(-6px);background:#6c3fc5;}
  }

  .input-area {
    background: #ffffff;
    padding: 12px 14px 20px;
    flex-shrink: 0;
    border-top: 1px solid #E2E8F0;
  }

  .status-bar {
    display:flex; align-items:center; gap:5px;
    font-size:10px; color:var(--text-dim);
    margin-bottom:8px; padding:0 4px;
    font-weight:600;
  }
  .status-dot { width:6px;height:6px;border-radius:50%;background:#4ADE80; }
  .status-dot.busy { background:#F59E0B; animation:pulse-green 0.8s infinite; }

  .input-row {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #F1F5F9;
    border-radius: 28px;
    padding: 6px 6px 6px 16px;
    border: 1.5px solid #E2E8F0;
    transition: border-color 0.2s;
  }
  .input-row:focus-within { border-color:#6c3fc5; box-shadow:0 0 0 3px rgba(108,63,197,0.1); }

  #userInput {
    flex:1; background:transparent; border:none; outline:none;
    font-family:'Nunito',sans-serif; font-size:14px; font-weight:500;
    color:var(--text-dark); resize:none;
    min-height:24px; max-height:100px;
    line-height:1.5;
  }
  #userInput::placeholder { color:#94A3B8; }

  .mic-btn {
    width:38px; height:38px; border-radius:50%;
    background:transparent; border:none;
    color:#94A3B8; font-size:18px; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition:all 0.2s; flex-shrink:0;
  }
  .mic-btn:hover { color:#6c3fc5; background:rgba(108,63,197,0.1); }

  #sendBtn {
    width:42px; height:42px; border-radius:50%;
    background:linear-gradient(135deg,#2563EB,#6c3fc5);
    border:none; color:white; font-size:18px;
    cursor:pointer; display:flex; align-items:center; justify-content:center;
    transition:all 0.2s; flex-shrink:0;
    box-shadow:0 4px 14px rgba(37,99,235,0.4);
  }
  #sendBtn:hover   { transform:scale(1.08); box-shadow:0 6px 20px rgba(37,99,235,0.5); }
  #sendBtn:disabled{ opacity:0.5; cursor:not-allowed; transform:none; }

  .hint { font-size:10px; color:var(--text-dim); text-align:center; margin-top:8px; font-weight:600; }

  @media (max-width:599px) {
    body { padding: 0; background: var(--chat-bg); }
    .phone { border-radius:0; box-shadow:none; height:100vh; max-height:none; }
    .header { border-radius:0; }
  }
</style>
</head>
<body>
<div class="phone">

  <!-- HEADER -->
  <div class="header">
    <div class="header-left">
      <div class="bot-avatar">🤖</div>
      <div class="header-info">
        <h1>Kamal Jeet AI</h1>
        <p><span class="online-dot"></span> Online — KJ Master AI</p>
      </div>
    </div>
    <div class="header-right">
      <button class="icon-btn" id="voiceBtn" onclick="toggleVoice()" title="Toggle Voice">🔊</button>
      <button class="icon-btn" onclick="clearChat()" title="Clear Chat">🗑️</button>
    </div>
  </div>

  <!-- CHAT -->
  <div id="chat">
    <div class="date-divider">Today</div>
  </div>

  <!-- INPUT -->
  <div class="input-area">
    <div class="status-bar">
      <div class="status-dot" id="statusDot"></div>
      <span id="statusText">Ready to chat</span>
    </div>
    <div class="input-row">
      <textarea id="userInput" placeholder="Type a message..." rows="1"
                onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
      <button class="mic-btn" title="Microphone">🎤</button>
      <button id="sendBtn" onclick="sendMessage()">➤</button>
    </div>
    <div class="hint">Enter to send &nbsp;•&nbsp; Hindi / Hinglish / English / Bengali / Punjabi</div>
  </div>

</div>

<script>
  let voiceEnabled = true;

  let audioUnlocked = false;
  let audioContext  = null;

  function unlockAudio() {
    if (audioUnlocked) return;
    try {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      if (audioContext.state === 'suspended') audioContext.resume();
      const buf = audioContext.createBuffer(1, 1, 22050);
      const src = audioContext.createBufferSource();
      src.buffer = buf;
      src.connect(audioContext.destination);
      src.start(0);
      audioUnlocked = true;
    } catch(e) {}
  }

  document.addEventListener('click',      unlockAudio, { once: false });
  document.addEventListener('touchstart', unlockAudio, { once: false });
  document.addEventListener('keydown',    unlockAudio, { once: false });

  function playAudio(base64Data) {
    return new Promise((resolve) => {
      try {
        unlockAudio();
        const audio = new Audio('data:audio/mp3;base64,' + base64Data);
        audio.volume = 1.0;
        audio.onended = () => resolve(true);
        audio.onerror = () => resolve(false);
        const p = audio.play();
        if (p !== undefined) {
          p.catch((err) => {
            if (audioContext) {
              const raw = atob(base64Data);
              const arr = new Uint8Array(raw.length);
              for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
              audioContext.decodeAudioData(arr.buffer, (decoded) => {
                const src = audioContext.createBufferSource();
                src.buffer = decoded;
                src.connect(audioContext.destination);
                src.onended = () => resolve(true);
                src.start(0);
              }, () => resolve(false));
            } else resolve(false);
          });
        }
      } catch(e) { resolve(false); }
    });
  }

  function toggleVoice() {
    voiceEnabled = !voiceEnabled;
    const btn = document.getElementById('voiceBtn');
    btn.textContent = voiceEnabled ? '🔊' : '🔇';
    btn.classList.toggle('voice-off', !voiceEnabled);
  }

  function setStatus(text, busy=false) {
    document.getElementById('statusText').textContent = text;
    document.getElementById('statusDot').className = 'status-dot' + (busy?' busy':'');
  }

  function getTime() {
    return new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'});
  }

  function addMessage(content, sender, isImage=false, imageUrl=null, caption=null) {
    const chat = document.getElementById('chat');
    if (sender === 'system') {
      const div = document.createElement('div');
      div.className = 'msg-row system';
      div.innerHTML = '<div class="bubble system">' + escapeHtml(content) + '</div>';
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
      return div;
    }
    const row = document.createElement('div');
    row.className = 'msg-row ' + sender;
    const avatarHtml = sender === 'user'
      ? '<div class="avatar user-av">👤</div>'
      : '<div class="avatar">🤖</div>';
    let bubbleContent = isImage && imageUrl
      ? '<img src="' + imageUrl + '" alt="' + escapeHtml(caption) + '" loading="lazy"><div class="img-caption">' + escapeHtml(caption) + '</div>'
      : escapeHtml(content);
    const wrapHtml = '<div class="bubble-wrap"><div class="bubble ' + sender + '">' + bubbleContent + '</div><div class="msg-time">' + getTime() + '</div></div>';
    row.innerHTML = sender === 'user' ? wrapHtml + avatarHtml : avatarHtml + wrapHtml;
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
    return row;
  }

  function addTyping() {
    const chat = document.getElementById('chat');
    const row = document.createElement('div');
    row.className = 'msg-row ai';
    row.id = 'typing';
    row.innerHTML = '<div class="avatar">🤖</div><div class="typing-bubble"><span></span><span></span><span></span></div>';
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
  }

  function removeTyping() {
    const t = document.getElementById('typing');
    if (t) t.remove();
  }

  function escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function handleKey(e) {
    if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 100) + 'px';
  }

  async function sendMessage() {
    const input = document.getElementById('userInput');
    const text  = input.value.trim();
    if (!text) return;
    unlockAudio();
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('sendBtn').disabled = true;
    setStatus('Typing...', true);
    addMessage(text, 'user');
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
        addMessage('', 'ai', true, data.image_url, data.caption);
      } else {
        addMessage(data.reply, 'ai');
        if (voiceEnabled && data.audio) {
          setStatus('Speaking...', true);
          await playAudio(data.audio);
        }
      }
      setStatus('Ready to chat');
    } catch(err) {
      removeTyping();
      addMessage('Connection error. Please try again.', 'ai');
      setStatus('Error', true);
    }
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('userInput').focus();
  }

  function clearChat() {
    fetch('/clear',{method:'POST'});
    const chat = document.getElementById('chat');
    chat.innerHTML = '<div class="date-divider">Today</div>';
    addMessage('Chat cleared. Start a new conversation!', 'system');
  }

  addMessage('Arre yaar, aa gaye! Main Kamal Jeet hoon — tera AI dost. Hindi, Hinglish, English, Bengali, Punjabi — sab mein baat kar!', 'ai');
  document.getElementById('userInput').focus();
</script>
</body>
</html>"""

# =============================================================
#                     HELPER FUNCTIONS
# =============================================================

def detect_language(text: str) -> str:
    bengali_chars = set('অআইঈউঊএঐওঔকখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়')
    if sum(1 for c in text if c in bengali_chars) > 2:
        return "bn"

    punjabi_chars = set('ਅਆਇਈਉਊਏਐਓਔਕਖਗਘਙਚਛਜਝਞਟਠਡਢਣਤਥਦਧਨਪਫਬਭਮਯਰਲਵਸ਼ਸਹ')
    if sum(1 for c in text if c in punjabi_chars) > 2:
        return "pa"

    hindi_chars = set('अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसहक्षत्रज्ञांःी')
    if sum(1 for c in text if c in hindi_chars) > 2:
        return "hi"

    hinglish_words = {"yaar","bhai","kya","hai","hoon","nahi","aur","mein","ki","ka","ko",
                      "se","karo","karta","karti","tha","thi","ho","hoga","kuch","sab",
                      "acha","theek","bahut","zyada","matlab","waise","seedha","bolo",
                      "dekho","suno","bata","bol","kar","le","de","hua",
                      "hui","aaj","kal","abhi","phir","toh","na","haan"}
    words = set(text.lower().split())
    if len(words & hinglish_words) >= 1:
        return "hinglish"

    punjabi_words = {"ki","karda","kardi","nahi","tenu","menu","teri","meri","pyaar",
                     "oye","sat sri akal","kiddan","theek","dasda","dasdi","chal","yaar",
                     "veer","paji","paaji","tussi","mainu","tainu","assi","tuhanu"}
    if len(words & punjabi_words) >= 2:
        return "pa_roman"

    return "en"


def clean_text(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*',     r'\1', text)
    text = re.sub(r'`(.*?)`',       r'\1', text)
    text = re.sub(r'#{1,6}\s',      '',    text)
    text = re.sub(r'^\s*[-*]\s',    '',    text, flags=re.MULTILINE)
    return text.strip()


def fetch_image_base64(query: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(query.replace(' ', '_'))
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
        url  = "https://www.bing.com/images/search?q=" + urllib.parse.quote(query)
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


# ✅ gTTS — Google TTS, works perfectly on Railway
def run_tts(text: str, lang: str) -> str | None:
    try:
        lang_map = {
            "hi":       "hi",
            "hinglish": "hi",
            "bn":       "bn",
            "pa":       "pa",
            "pa_roman": "pa",
            "en":       "en"
        }
        tts_lang = lang_map.get(lang, "en")

        buf = BytesIO()
        tts = gTTS(text=text, lang=tts_lang, slow=False)
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_data = buf.read()

        if len(audio_data) == 0:
            print("❌ TTS: Empty audio")
            return None

        print(f"✅ TTS: Generated {len(audio_data)} bytes for lang={lang}")
        return base64.b64encode(audio_data).decode()
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return None


# =============================================================
#                     ROUTES
# =============================================================

@app.route("/")
def index():
    resp = render_template_string(HTML)
    if isinstance(resp, str):
        return resp.encode('utf-8'), 200, {'Content-Type': 'text/html; charset=utf-8'}
    return resp


@app.route("/chat", methods=["POST"])
def chat():
    data         = request.json
    user_message = data.get("message", "")
    want_voice   = data.get("voice", True)

    user_lang = detect_language(user_message)
    lang_instruction = {
        "hi":       "[STRICT: User wrote in Hindi. Reply ONLY in pure Hindi Devanagari script.]",
        "hinglish": "[STRICT: User wrote in Hinglish. Reply ONLY in Hinglish Roman script.]",
        "bn":       "[STRICT: User wrote in Bengali. Reply ONLY in natural Bengali (Bangla) script.]",
        "pa":       "[STRICT: User wrote in Punjabi Gurmukhi script. Reply ONLY in Punjabi Gurmukhi script.]",
        "pa_roman": "[STRICT: User wrote in Romanized Punjabi. Reply ONLY in Romanized Punjabi.]",
        "en":       "[STRICT: User wrote in English. Reply ONLY in English.]"
    }.get(user_lang, "[STRICT: Reply in the same language the user used.]")

    forced_message = lang_instruction + "\n\nUser: " + user_message
    chat_history.append({"role": "user", "content": forced_message})

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + chat_history,
            max_tokens=MAX_TOKENS,
            temperature=0.9
        )
        reply = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": reply})
        if len(chat_history) > 20:
            chat_history.pop(0)
            chat_history.pop(0)
    except Exception as e:
        return jsonify({"type": "text", "reply": "Yaar kuch error aa gaya: " + str(e)})

    image_match = re.match(r'^\[IMAGE:(.*?)\]$', reply.strip())
    if image_match:
        query     = image_match.group(1)
        image_url = fetch_image_base64(query)
        return jsonify({"type": "image", "image_url": image_url, "caption": query})

    reply = clean_text(reply)

    audio_b64 = None
    if want_voice:
        audio_b64 = run_tts(reply, user_lang)

    return jsonify({"type": "text", "reply": reply, "audio": audio_b64})


@app.route("/clear", methods=["POST"])
def clear():
    chat_history.clear()
    return jsonify({"status": "ok"})


# =============================================================
#   ✅ RAILWAY FIX — Dynamic PORT
# =============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("  Kamal Jeet AI v3.2 — Railway Ready!")
    print("  Port:", port)
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)