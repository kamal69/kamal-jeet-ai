import os, base64, urllib.request, urllib.parse, re, json
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs

load_dotenv()
app = Flask(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven  = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
history = []

SYSTEM = (
    "You are Sarthi AI made by Kamal Jeet. "
    "You understand Hindi, English and Hinglish. "
    "Reply in the same language the user uses. "
    "Keep replies short. "
    "For image requests reply ONLY: [IMAGE:query]"
)

# ------------------------------------------------------------------
# HTML is built with Python string concatenation — zero escape risk
# ------------------------------------------------------------------

CSS = """
<style>
:root{--bg:#0d0d0d;--sb:#111;--s1:#1a1a1a;--s2:#222;--br:#2a2a2a;
      --ac:#c96442;--ac2:#e07a52;--tx:#ececec;--mu:#888;--cb:#161616;--r:12px}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--tx);font-family:'Sora',sans-serif;display:flex;height:100vh}
#sb{width:240px;background:var(--sb);border-right:1px solid var(--br);
    display:flex;flex-direction:column;padding:20px 14px;gap:8px;flex-shrink:0}
.logo{display:flex;align-items:center;gap:10px;padding:8px 10px 18px;
      border-bottom:1px solid var(--br);margin-bottom:6px}
.lt{font-size:15px;font-weight:600} .ls{font-size:10px;color:var(--mu)}
.nb{display:flex;align-items:center;gap:8px;padding:9px 12px;
    background:var(--s2);border:1px solid var(--br);border-radius:var(--r);
    color:var(--tx);font-family:'Sora',sans-serif;font-size:13px;cursor:pointer;width:100%;text-align:left}
.nb:hover{background:var(--s1);border-color:var(--ac)}
.sl{font-size:10px;font-weight:500;color:var(--mu);text-transform:uppercase;letter-spacing:1px;padding:8px 10px 4px}
.ci{padding:8px 10px;border-radius:8px;font-size:12.5px;color:var(--mu);cursor:pointer;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ci.on{background:var(--s2);color:var(--tx)}
.sf{margin-top:auto;padding-top:12px;border-top:1px solid var(--br)}
.up{display:flex;align-items:center;gap:9px;padding:8px 10px;border-radius:8px;cursor:pointer}
.up:hover{background:var(--s2)}
.ua{width:28px;height:28px;background:linear-gradient(135deg,var(--ac),#7c3aed);
    border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-size:12px;font-weight:600;flex-shrink:0}
#mn{flex:1;display:flex;flex-direction:column;overflow:hidden}
#tb{display:flex;align-items:center;justify-content:space-between;
    padding:14px 24px;border-bottom:1px solid var(--br);flex-shrink:0}
.bg{display:flex;align-items:center;gap:6px;padding:5px 12px;
    background:var(--s1);border:1px solid var(--br);border-radius:20px;font-size:12px;color:var(--mu)}
.gd{width:6px;height:6px;background:#22c55e;border-radius:50%}
#st{font-size:12px;color:var(--mu);padding:4px 12px;border-radius:20px;
    background:var(--s1);border:1px solid var(--br)}
.cb2{background:none;border:1px solid var(--br);color:var(--mu);padding:5px 12px;
     border-radius:20px;cursor:pointer;font-size:12px;font-family:'Sora',sans-serif}
.cb2:hover{border-color:#ef4444;color:#ef4444}
#ch{flex:1;overflow-y:auto;padding:32px 0;display:flex;flex-direction:column;scroll-behavior:smooth}
#ch::-webkit-scrollbar{width:4px}
#ch::-webkit-scrollbar-thumb{background:var(--br);border-radius:4px}
#wl{display:flex;flex-direction:column;align-items:center;justify-content:center;
    gap:16px;padding:40px;text-align:center;min-height:100%}
.wi{width:56px;height:56px;background:linear-gradient(135deg,var(--ac),#9333ea);
    border-radius:16px;display:flex;align-items:center;justify-content:center;
    font-size:28px;box-shadow:0 0 40px rgba(201,100,66,.25)}
.wt{font-size:26px;font-weight:600} .ws{font-size:14px;color:var(--mu);max-width:360px;line-height:1.6}
.sg{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px;width:100%;max-width:500px}
.sc{background:var(--s1);border:1px solid var(--br);border-radius:var(--r);padding:12px 14px;
    font-size:13px;color:var(--mu);cursor:pointer;text-align:left;line-height:1.4;transition:all .18s}
.sc:hover{border-color:var(--ac);color:var(--tx);background:var(--s2)}
.sc strong{display:block;color:var(--tx);font-size:12px;margin-bottom:3px}
.rw{padding:16px 24px;display:flex;gap:14px;max-width:820px;width:100%;margin:0 auto}
.rw.u{flex-direction:row-reverse}
.av{width:34px;height:34px;border-radius:50%;flex-shrink:0;display:flex;
    align-items:center;justify-content:center;font-size:13px;font-weight:700;margin-top:2px}
.av.ai{background:linear-gradient(135deg,var(--ac),#9333ea)}
.av.u{background:linear-gradient(135deg,#2563eb,#7c3aed)}
.bb{max-width:680px;font-size:14.5px;line-height:1.75;color:var(--tx);word-wrap:break-word}
.rw.u .bb{background:var(--s2);border:1px solid var(--br);
           border-radius:16px 4px 16px 16px;padding:11px 16px}
.bb p{margin:0 0 8px} .bb p:last-child{margin-bottom:0}
.bb strong{color:#fbbf24}
.bb code{font-family:'JetBrains Mono',monospace;background:var(--cb);color:#7dd3fc;
         padding:2px 6px;border-radius:5px;font-size:13px}
.cw{margin:10px 0;border-radius:10px;overflow:hidden;border:1px solid var(--br)}
.ch2{display:flex;align-items:center;justify-content:space-between;background:#1c1c1c;
     padding:7px 14px;font-size:11px;color:var(--mu);font-family:'JetBrains Mono',monospace}
.bb pre{background:var(--cb);padding:14px 16px;overflow-x:auto;margin:0}
.bb pre code{background:none;padding:0;color:#e2e8f0}
.cpb{background:var(--s2);border:1px solid var(--br);color:var(--mu);padding:3px 10px;
     border-radius:5px;font-size:11px;cursor:pointer;font-family:'Sora',sans-serif}
.cpb:hover{border-color:var(--ac);color:var(--tx)}
.iw img{max-width:300px;border-radius:var(--r);border:1px solid var(--br);display:block}
.il{font-size:11px;color:var(--mu);margin-top:5px}
.td{display:flex;gap:5px;padding:8px 0;align-items:center}
.td span{width:7px;height:7px;background:var(--mu);border-radius:50%;animation:bl 1.2s infinite}
.td span:nth-child(2){animation-delay:.2s} .td span:nth-child(3){animation-delay:.4s}
@keyframes bl{0%,80%,100%{opacity:.2}40%{opacity:1}}
#iw2{padding:16px 24px 20px;border-top:1px solid var(--br);flex-shrink:0}
.ib{max-width:820px;margin:0 auto;background:var(--s1);border:1px solid var(--br);
    border-radius:14px;display:flex;align-items:flex-end;gap:8px;padding:10px 12px;transition:border-color .2s}
.ib:focus-within{border-color:var(--ac)}
#ti{flex:1;background:none;border:none;outline:none;color:var(--tx);
    font-family:'Sora',sans-serif;font-size:14px;line-height:1.5;
    resize:none;padding:3px 4px;height:26px;min-height:26px;max-height:140px;overflow-y:hidden}
#ti::placeholder{color:var(--mu)}
.ib2{width:36px;height:36px;border:none;border-radius:9px;background:var(--s2);
     color:var(--mu);cursor:pointer;display:flex;align-items:center;
     justify-content:center;font-size:16px;flex-shrink:0}
.ib2:hover{background:var(--br);color:var(--tx)} .ib2.on{background:#dc2626;color:white}
#tkb{padding:0 14px;height:36px;border-radius:9px;background:var(--s2);border:1px solid var(--br);
     color:var(--mu);cursor:pointer;font-family:'Sora',sans-serif;font-size:12px;
     font-weight:500;flex-shrink:0;white-space:nowrap}
#tkb:hover{border-color:#22c55e;color:#22c55e} #tkb.on{background:#dc2626;border-color:#dc2626;color:white}
#sb2{width:36px;height:36px;border:none;border-radius:9px;background:var(--ac);
     color:white;cursor:pointer;display:flex;align-items:center;
     justify-content:center;font-size:16px;flex-shrink:0}
#sb2:hover{background:var(--ac2)} 
.ht{text-align:center;font-size:11px;color:var(--mu);margin-top:8px}
@media(max-width:640px){#sb{display:none}.rw{padding:12px 14px}#iw2{padding:12px 14px 16px}}
</style>
"""

BODY = """
<div id="sb">
  <div class="logo">
    <svg width="32" height="32" viewBox="0 0 36 36">
      <rect width="36" height="36" rx="10" fill="#1a1a1a" stroke="#2a2a2a" stroke-width="1"/>
      <circle cx="18" cy="18" r="10" fill="none" stroke="#c96442" stroke-width="1.5"/>
      <circle cx="18" cy="18" r="6" fill="#c96442" opacity="0.15"/>
      <polygon points="18,8 20,14 18,12 16,14" fill="#c96442"/>
      <circle cx="18" cy="18" r="2.5" fill="#c96442"/>
    </svg>
    <div><div class="lt">Sarthi AI</div><div class="ls">Powered by Kamal Jeet</div></div>
  </div>
  <button class="nb" id="ncb">&#9997; New Chat</button>
  <div class="sl">Recent</div>
  <div class="ci on" id="cl">New conversation</div>
  <div class="sf">
    <div class="up">
      <div class="ua">KJ</div>
      <div>
        <div style="font-size:12.5px;font-weight:500">Kamal Jeet</div>
        <div style="font-size:11px;color:var(--mu)">Himachal Pradesh</div>
      </div>
    </div>
  </div>
</div>

<div id="mn">
  <div id="tb">
    <div class="bg"><div class="gd"></div> Online</div>
    <div style="display:flex;gap:10px;align-items:center">
      <button class="cb2" id="clb">&#128465; Clear</button>
      <div id="st">Ready</div>
    </div>
  </div>

  <div id="ch">
    <div id="wl">
      <div class="wi">&#129302;</div>
      <div class="wt">Sarthi AI</div>
      <div class="ws">Hindi, English, Hinglish &mdash; sab samajhta hun.</div>
      <div class="sg">
        <div class="sc" data-q="Python mein inheritance kya hota hai?"><strong>&#128187; Code</strong>Python inheritance explain karo</div>
        <div class="sc" data-q="Taj Mahal ki image dikhao"><strong>&#128444; Image</strong>Taj Mahal dikhao</div>
        <div class="sc" data-q="Aaj ka weather kaisa hai?"><strong>&#128172; Baat</strong>Koi bhi sawaal poochho</div>
        <div class="sc" data-q="Mujhe motivate karo"><strong>&#10024; Motivation</strong>Motivational quote do</div>
      </div>
    </div>
  </div>

  <div id="iw2">
    <div class="ib">
      <textarea id="ti" placeholder="Kuch bhi poochho..."></textarea>
      <button class="ib2" id="mb">&#127908;</button>
      <button id="tkb">&#128257; Talk</button>
      <button id="sb2">&#9658;</button>
    </div>
    <div class="ht">Enter = send &nbsp;&middot;&nbsp; Shift+Enter = new line</div>
  </div>
</div>
"""

JS = """
<script>
var isL=false, isTM=false, rec=null, curAud=null, mc=0;
var ti=document.getElementById('ti');
var sb2=document.getElementById('sb2');
var mb=document.getElementById('mb');
var tkb=document.getElementById('tkb');
var ch=document.getElementById('ch');

// Suggestion cards & copy buttons via delegation
ch.addEventListener('click', function(e){
  var sc=e.target.closest('.sc');
  if(sc){ ti.value=sc.getAttribute('data-q'); doSend(); return; }
  var cp=e.target.closest('.cpb');
  if(cp){
    var el=document.getElementById(cp.getAttribute('data-id'));
    if(el) navigator.clipboard.writeText(el.innerText).then(function(){
      cp.textContent='Copied!'; setTimeout(function(){ cp.textContent='Copy'; },2000);
    });
  }
});

// Textarea resize
ti.addEventListener('input', function(){
  this.style.height='26px';
  var h=this.scrollHeight;
  this.style.height=(h>140?140:h)+'px';
  this.style.overflowY=h>140?'auto':'hidden';
});

// Enter to send
ti.addEventListener('keydown', function(e){
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); doSend(); }
});

sb2.addEventListener('click', function(){ doSend(); });
document.getElementById('clb').addEventListener('click', doClear);
document.getElementById('ncb').addEventListener('click', doClear);
mb.addEventListener('click', function(){ if(isL) stopL(); else startL(); });
tkb.addEventListener('click', doToggleTalk);

// Unlock audio
document.addEventListener('click', function(){
  var a=new Audio();
  a.src='data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAA';
  a.play().catch(function(){});
},{once:true});

function setSt(m){ document.getElementById('st').textContent=m; }

function safeCan(){
  try{ if(window.speechSynthesis) window.speechSynthesis.cancel(); }catch(e){}
}

function escH(t){
  return (t||'').split('&').join('&amp;').split('<').join('&lt;').split('>').join('&gt;');
}

// Simple markdown renderer — NO regex
function renderMD(raw){
  if(!raw) return '';
  var out='';
  // Split on code blocks manually
  var i=0, txt=raw;
  while(i < txt.length){
    var ci=txt.indexOf('```',i);
    if(ci===-1){
      out+=inlineRender(txt.slice(i));
      break;
    }
    if(ci > i) out+=inlineRender(txt.slice(i,ci));
    var ce=txt.indexOf('```',ci+3);
    if(ce===-1){ out+=inlineRender(txt.slice(ci)); break; }
    var block=txt.slice(ci+3,ce);
    
    var lang='code', code=block;
    if(nl!==-1){
      var fl=block.slice(0,nl).trim();
      if(fl && fl.length<20 && fl.indexOf(' ')===-1){ lang=fl; code=block.slice(nl+1); }
    }
    var cid='c'+Math.random().toString(36).slice(2,7);
    out+='<div class="cw"><div class="ch2"><span>'+escH(lang)+'</span>'
        +'<button class="cpb" data-id="'+cid+'">Copy</button></div>'
        +'<pre><code id="'+cid+'">'+escH(code.trim())+'</code></pre></div>';
    i=ce+3;
  }
  return out;
}

function inlineRender(s){
  if(!s.trim()) return '';
  var out='', i=0;
  while(i<s.length){
    // Bold **
    if(s.slice(i,i+2)==='**'){
      var e=s.indexOf('**',i+2);
      if(e!==-1){ out+='<strong>'+escH(s.slice(i+2,e))+'</strong>'; i=e+2; continue; }
    }
    // Inline code `
    if(s[i]==='`'){
      var e2=s.indexOf('`',i+1);
      if(e2!==-1){ out+='<code>'+escH(s.slice(i+1,e2))+'</code>'; i=e2+1; continue; }
    }
    // Newline
    if(s[i]==='\n'){ out+='<br>'; i++; continue; }
    out+=escH(s[i]); i++;
  }
  return out ? '<p>'+out+'</p>' : '';
}

function scrollD(){ ch.scrollTop=ch.scrollHeight; }

function remWel(){ var w=document.getElementById('wl'); if(w) w.remove(); }

function addUser(t){
  remWel(); mc++;
  if(mc===1) document.getElementById('cl').textContent=t.slice(0,28)+(t.length>28?'...':'');
  var r=document.createElement('div');
  r.className='rw u';
  r.innerHTML='<div class="av u">KJ</div><div class="bb"><p>'+escH(t)+'</p></div>';
  ch.appendChild(r); scrollD();
}

function addAI(t){
  var tr=document.getElementById('tr'); if(tr) tr.remove();
  var r=document.createElement('div');
  r.className='rw';
  r.innerHTML='<div class="av ai">S</div><div class="bb">'+renderMD(t||'')+'</div>';
  ch.appendChild(r); scrollD();
}

function addTyping(){
  remWel();
  var r=document.createElement('div');
  r.className='rw'; r.id='tr';
  r.innerHTML='<div class="av ai">S</div><div class="bb"><div class="td"><span></span><span></span><span></span></div></div>';
  ch.appendChild(r); scrollD();
}

function addImg(src,lbl){
  var tr=document.getElementById('tr'); if(tr) tr.remove();
  var r=document.createElement('div');
  r.className='rw';
  r.innerHTML='<div class="av ai">S</div><div class="bb"><div class="iw">'
    +'<img src="'+src+'" onerror="this.parentElement.innerHTML=\'Image load nahi hui\'">'
    +'<div class="il">'+escH(lbl||'Image')+'</div></div></div>';
  ch.appendChild(r); scrollD();
}

function welHTML(){
  return '<div class="wi">&#129302;</div>'
    +'<div class="wt">Sarthi AI</div>'
    +'<div class="ws">Hindi, English, Hinglish &mdash; sab samajhta hun.</div>'
    +'<div class="sg">'
    +'<div class="sc" data-q="Python mein inheritance kya hota hai?"><strong>&#128187; Code</strong>Python inheritance explain karo</div>'
    +'<div class="sc" data-q="Taj Mahal ki image dikhao"><strong>&#128444; Image</strong>Taj Mahal dikhao</div>'
    +'<div class="sc" data-q="Aaj ka weather kaisa hai?"><strong>&#128172; Baat</strong>Koi bhi sawaal poochho</div>'
    +'<div class="sc" data-q="Mujhe motivate karo"><strong>&#10024; Motivation</strong>Motivational quote do</div>'
    +'</div>';
}

function doClear(){
  mc=0; ch.innerHTML='';
  var w=document.createElement('div');
  w.id='wl'; w.innerHTML=welHTML();
  ch.appendChild(w);
  document.getElementById('cl').textContent='New conversation';
  setSt('Ready');
  fetch('/clear',{method:'POST'}).catch(function(){});
}

function doSend(){
  var msg=ti.value.trim();
  if(!msg) return;
  addUser(msg);
  ti.value=''; ti.style.height='26px'; ti.style.overflowY='hidden';
  addTyping(); setSt('Thinking...');

  fetch('/chat',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:msg})
  })
  .then(function(r){ return r.json(); })
  .then(function(d){
    if(d.type==='image'){
      if(d.image_url) addImg(d.image_url, d.query||'');
      else addAI('Image nahi mili: '+(d.query||''));
      setSt('Ready');
      if(isTM) startL();
      return;
    }
    var rep=d.reply||'';
    addAI(rep);
    if(d.audio){
      if(curAud){ curAud.pause(); curAud=null; }
      safeCan();
      var au=new Audio('data:audio/mp3;base64,'+d.audio);
      curAud=au; setSt('Speaking...');
      au.onended=function(){ curAud=null; setSt('Ready'); if(isTM) startL(); };
      au.onerror=function(){ curAud=null; spk(rep,function(){ if(isTM) startL(); }); };
      au.play().catch(function(){ spk(rep,function(){ if(isTM) startL(); }); });
    } else {
      spk(rep, function(){ if(isTM) startL(); });
    }
  })
  .catch(function(e){
    var tr=document.getElementById('tr'); if(tr) tr.remove();
    addAI('Error: '+e.message); setSt('Error');
    if(isTM) startL();
  });
}

function spk(text,onEnd){
  if(!text||!window.speechSynthesis){ if(onEnd) onEnd(); return; }
  safeCan();
  // Clean text without regex
  var clean=text, i=0, out='';
  // Remove code blocks
  while(i<clean.length){
    var ci=clean.indexOf('```',i);
    if(ci===-1){ out+=clean.slice(i); break; }
    if(ci>i) out+=clean.slice(i,ci);
    var ce=clean.indexOf('```',ci+3);
    if(ce===-1) break;
    out+=' code block. '; i=ce+3;
  }
  clean=out;
  // Remove ** and `
  clean=clean.split('**').join('');
  clean=clean.split('`').join('');
  clean=clean.trim();
  if(!clean){ if(onEnd) onEnd(); return; }

  var chunks=[], cur='', words=clean.split(' ');
  for(var w=0;w<words.length;w++){
    cur+=(cur?' ':'')+words[w];
    if(cur.length>150){ chunks.push(cur); cur=''; }
  }
  if(cur) chunks.push(cur);
  if(!chunks.length){ if(onEnd) onEnd(); return; }

  var voices=window.speechSynthesis.getVoices();
  var idx=0;
  var ka=setInterval(function(){
    if(!window.speechSynthesis||!window.speechSynthesis.speaking){ clearInterval(ka); return; }
    window.speechSynthesis.pause(); window.speechSynthesis.resume();
  },10000);

  function nxt(){
    if(idx>=chunks.length){ clearInterval(ka); setSt('Ready'); if(onEnd) onEnd(); return; }
    var u=new SpeechSynthesisUtterance(chunks[idx++]);
    var isH=false;
    for(var c=0;c<u.text.length;c++){
      var code=u.text.charCodeAt(c);
      if(code>=0x0900 && code<=0x097F){ isH=true; break; }
    }
    var v=null;
    for(var vi=0;vi<voices.length;vi++){
      if(isH && voices[vi].lang.slice(0,2)==='hi'){ v=voices[vi]; break; }
      if(!isH && voices[vi].lang==='en-IN'){ v=voices[vi]; break; }
    }
    if(!v) for(var vi=0;vi<voices.length;vi++){
      if(voices[vi].lang.slice(0,2)==='en'){ v=voices[vi]; break; }
    }
    if(v) u.voice=v;
    u.lang=isH?'hi-IN':'en-IN'; u.rate=0.92; u.pitch=1.0; u.volume=1.0;
    u.onend=nxt;
    u.onerror=function(){ clearInterval(ka); setSt('Ready'); if(onEnd) onEnd(); };
    window.speechSynthesis.speak(u);
  }
  setSt('Speaking...'); nxt();
}

if(window.speechSynthesis && window.speechSynthesis.onvoiceschanged!==undefined){
  window.speechSynthesis.onvoiceschanged=function(){ window.speechSynthesis.getVoices(); };
}

function doToggleTalk(){
  isTM=!isTM;
  if(isTM){
    tkb.textContent='Stop'; tkb.classList.add('on');
    setSt('Talk Mode ON'); startL();
  } else {
    tkb.textContent='Talk'; tkb.classList.remove('on');
    stopL(); safeCan();
    if(curAud){ curAud.pause(); curAud=null; }
    setSt('Ready');
  }
}

function bldRec(){
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){ alert('Chrome use karein mic ke liye!'); return null; }
  var r=new SR();
  r.lang='hi-IN'; r.interimResults=false; r.maxAlternatives=1;
  r.onstart=function(){ isL=true; mb.classList.add('on'); setSt('Listening...'); };
  r.onresult=function(e){ ti.value=e.results[0][0].transcript; stopL(); doSend(); };
  r.onerror=function(e){ stopL(); setSt('Mic error: '+e.error); };
  r.onend=function(){ stopL(); };
  return r;
}

function startL(){
  if(isL) return;
  safeCan();
  if(curAud){ curAud.pause(); curAud=null; }
  rec=bldRec(); if(!rec) return;
  try{ rec.start(); }catch(e){ console.warn(e); }
}

function stopL(){
  isL=false; mb.classList.remove('on');
  if(rec){ try{ rec.stop(); }catch(e){} rec=null; }
}
</script>
"""

def build_html():
    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Sarthi AI</title>"
        "<link href='https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600"
        "&family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>"
        + CSS +
        "</head><body>"
        + BODY + JS +
        "</body></html>"
    )

HTML_FINAL = build_html().encode("utf-8")


# ── Routes ──────────────────────────────────────────

@app.route("/")
def home():
    return Response(HTML_FINAL, mimetype="text/html")

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

    sr = web_search(msg)
    if sr:
        messages.insert(1, {"role": "system", "content": "Web info:\n" + sr})

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=300,
        temperature=0.7
    )
    reply = resp.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    m = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
    if m:
        q = m.group(1)
        return jsonify({"type": "image", "image_url": fetch_image(q), "query": q})

    return jsonify({"reply": reply, "audio": eleven_tts(reply)})


# ── Helpers ─────────────────────────────────────────

def eleven_tts(text):
    try:
        clean = text
        # Remove code blocks
        while '```' in clean:
            s = clean.find('```')
            e = clean.find('```', s+3)
            if e == -1: break
            clean = clean[:s] + ' code block. ' + clean[e+3:]
        clean = clean.replace('**','').replace('`','').strip()
        if not clean: return None
        ag = eleven.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            model_id="eleven_multilingual_v2",
            text=clean,
            output_format="mp3_44100_128",
        )
        ab = b"".join(ag)
        if not ab: return None
        print("ElevenLabs OK -- " + str(len(ab)) + " bytes")
        return base64.b64encode(ab).decode()
    except Exception as e:
        print("ElevenLabs ERROR: " + str(e))
        return None

def web_search(query):
    if not TAVILY_API_KEY: return None
    try:
        payload = json.dumps({"api_key": TAVILY_API_KEY, "query": query, "max_results": 3}).encode()
        req = urllib.request.Request(
            "https://api.tavily.com/search", data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
        if d.get("answer"): return d["answer"]
        return " ".join([x.get("content","")[:200] for x in d.get("results",[])])
    except Exception as e:
        print("Search error: " + str(e))
        return None

def fetch_image(query):
    try:
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action":"query","titles":query,"prop":"pageimages","pithumbsize":600,"format":"json"
        })
        with urllib.request.urlopen(url) as r:
            d = json.loads(r.read().decode())
        for page in d["query"]["pages"].values():
            if "thumbnail" in page: return page["thumbnail"]["source"]
    except: pass
    return None

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
