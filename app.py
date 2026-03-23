var isL = false, isTM = false, rec = null, curAud = null, mc = 0;

var ti   = document.getElementById('ti');
var snd  = document.getElementById('snd');
var mb   = document.getElementById('mb');
var tkb  = document.getElementById('tkb');
var ch   = document.getElementById('ch');
var clbtn= document.getElementById('clbtn');
var ncb  = document.getElementById('ncb');

// Event listeners
snd.addEventListener('click',    function(){ doSend(); });
clbtn.addEventListener('click',  function(){ doClear(); });
ncb.addEventListener('click',    function(){ doClear(); });
mb.addEventListener('click',     function(){ if(isL){ stopL(); } else { startL(); } });
tkb.addEventListener('click',    function(){ doToggleTalk(); });

ti.addEventListener('input', function(){
    this.style.height = '26px';
    var h = this.scrollHeight;
    this.style.height = (h > 140 ? 140 : h) + 'px';
    this.style.overflowY = h > 140 ? 'auto' : 'hidden';
});

ti.addEventListener('keydown', function(e){
    if(e.key === 'Enter' && !e.shiftKey){
        e.preventDefault();
        doSend();
    }
});

// Delegation for suggestion cards and copy buttons
ch.addEventListener('click', function(e){
    var sc = e.target.closest('.sc');
    if(sc){
        ti.value = sc.getAttribute('data-q');
        doSend();
        return;
    }
    var cp = e.target.closest('.cpb');
    if(cp){
        var el = document.getElementById(cp.getAttribute('data-id'));
        if(el){
            navigator.clipboard.writeText(el.innerText).then(function(){
                cp.textContent = 'Copied!';
                setTimeout(function(){ cp.textContent = 'Copy'; }, 2000);
            });
        }
    }
});

// Unlock audio autoplay
document.addEventListener('click', function(){
    var a = new Audio();
    a.src = 'data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAA';
    a.play().catch(function(){});
}, { once: true });

function setSt(m){
    document.getElementById('st').textContent = m;
}

function safeCan(){
    try {
        if(window.speechSynthesis){ window.speechSynthesis.cancel(); }
    } catch(e){}
}

function escH(t){
    var s = t || '';
    var out = '';
    for(var i = 0; i < s.length; i++){
        var c = s[i];
        if(c === '&'){ out += '&amp;'; }
        else if(c === '<'){ out += '&lt;'; }
        else if(c === '>'){ out += '&gt;'; }
        else { out += c; }
    }
    return out;
}

function renderMD(raw){
    if(!raw){ return ''; }
    var out = '';
    var i = 0;
    while(i < raw.length){
        var ci = raw.indexOf('```', i);
        if(ci === -1){
            out += inlineRender(raw.slice(i));
            break;
        }
        if(ci > i){ out += inlineRender(raw.slice(i, ci)); }
        var ce = raw.indexOf('```', ci + 3);
        if(ce === -1){
            out += inlineRender(raw.slice(ci));
            break;
        }
        var block = raw.slice(ci + 3, ce);
        var nl = block.indexOf('\n');
        var lang = 'code';
        var code = block;
        if(nl !== -1){
            var fl = block.slice(0, nl).trim();
            if(fl && fl.length < 20 && fl.indexOf(' ') === -1){
                lang = fl;
                code = block.slice(nl + 1);
            }
        }
        var cid = 'c' + Math.random().toString(36).slice(2, 7);
        out += '<div class="cw"><div class="ch2"><span>' + escH(lang) + '</span>'
             + '<button class="cpb" data-id="' + cid + '">Copy</button></div>'
             + '<pre><code id="' + cid + '">' + escH(code.trim()) + '</code></pre></div>';
        i = ce + 3;
    }
    return out;
}

function inlineRender(s){
    if(!s.trim()){ return ''; }
    var out = '';
    var i = 0;
    while(i < s.length){
        if(s.slice(i, i+2) === '**'){
            var e = s.indexOf('**', i + 2);
            if(e !== -1){
                out += '<strong>' + escH(s.slice(i+2, e)) + '</strong>';
                i = e + 2;
                continue;
            }
        }
        if(s[i] === '`'){
            var e2 = s.indexOf('`', i + 1);
            if(e2 !== -1){
                out += '<code>' + escH(s.slice(i+1, e2)) + '</code>';
                i = e2 + 1;
                continue;
            }
        }
        if(s[i] === '\n'){
            out += '<br>';
            i++;
            continue;
        }
        out += escH(s[i]);
        i++;
    }
    return out ? '<p>' + out + '</p>' : '';
}

function scrollD(){ ch.scrollTop = ch.scrollHeight; }
function remWel(){ var w = document.getElementById('wl'); if(w){ w.remove(); } }

function addUser(t){
    remWel();
    mc++;
    if(mc === 1){
        document.getElementById('cl').textContent = t.slice(0, 28) + (t.length > 28 ? '...' : '');
    }
    var r = document.createElement('div');
    r.className = 'rw u';
    r.innerHTML = '<div class="av u">KJ</div><div class="bb"><p>' + escH(t) + '</p></div>';
    ch.appendChild(r);
    scrollD();
}

// ============================================================
// 🤖 ROBOT TYPEWRITER EFFECT
// ============================================================
function addAI(fullText, onDone){
    var tr = document.getElementById('tr');
    if(tr){ tr.remove(); }

    var r = document.createElement('div');
    r.className = 'rw';

    // Robot prefix badge
    var bbDiv = document.createElement('div');
    bbDiv.className = 'bb';

    r.innerHTML = '<div class="av ai">S</div>';
    r.appendChild(bbDiv);
    ch.appendChild(r);
    scrollD();

    // Check if reply has code blocks — render instantly if so
    var hasCodeBlock = fullText.indexOf('```') !== -1;

    if(hasCodeBlock){
        // Code blocks: render instantly (can't typewrite HTML safely)
        bbDiv.innerHTML = renderMD(fullText);
        scrollD();
        if(onDone){ onDone(); }
        return;
    }

    // Plain text: Robot typewriter character by character
    var displayed = '';
    var i = 0;
    var speed = 18; // ms per character — robot speed

    // Blinking cursor element
    var cursor = document.createElement('span');
    cursor.className = 'robot-cursor';
    cursor.textContent = '▮';
    bbDiv.appendChild(cursor);

    function typeNext(){
        if(i >= fullText.length){
            // Done — remove cursor, render final markdown
            cursor.remove();
            bbDiv.innerHTML = renderMD(fullText);
            scrollD();
            if(onDone){ onDone(); }
            return;
        }

        // Take next character
        displayed += fullText[i];
        i++;

        // Render partial markdown inline for bold/code, else plain
        // For typewriter: just show raw text with cursor at end
        bbDiv.innerHTML = '';

        // Show partial rendered text
        var textNode = document.createElement('span');
        textNode.className = 'robot-typing';
        // Simple partial render — just escape and show
        textNode.innerHTML = escH(displayed).replace(/\n/g, '<br>');
        bbDiv.appendChild(textNode);

        // Re-attach blinking cursor
        var c2 = document.createElement('span');
        c2.className = 'robot-cursor';
        c2.textContent = '▮';
        bbDiv.appendChild(c2);
        cursor = c2;

        scrollD();

        // Slightly vary speed for robot feel
        var delay = speed;
        // Pause longer at punctuation
        var ch2 = fullText[i-1];
        if(ch2 === '.' || ch2 === '!' || ch2 === '?' || ch2 === '\n'){
            delay = speed * 6;
        } else if(ch2 === ',' || ch2 === ';' || ch2 === ':'){
            delay = speed * 3;
        }

        setTimeout(typeNext, delay);
    }

    // Small initial delay before robot starts "thinking"
    setTimeout(typeNext, 120);
}

function addTyping(){
    remWel();
    var r = document.createElement('div');
    r.className = 'rw';
    r.id = 'tr';
    r.innerHTML = '<div class="av ai">S</div><div class="bb"><div class="td"><span></span><span></span><span></span></div></div>';
    ch.appendChild(r);
    scrollD();
}

function addImg(src, lbl){
    var tr = document.getElementById('tr');
    if(tr){ tr.remove(); }
    var r = document.createElement('div');
    r.className = 'rw';
    r.innerHTML = '<div class="av ai">S</div><div class="bb"><div class="iw">'
        + '<img src="' + src + '" onerror="this.parentElement.innerHTML=\'Image load nahi hui\'">'
        + '<div class="il">' + escH(lbl || 'Image') + '</div></div></div>';
    ch.appendChild(r);
    scrollD();
}

function welHTML(){
    return '<div class="wi">&#129302;</div>'
        + '<div class="wt">Sarthi AI</div>'
        + '<div class="ws">Hindi, English, Hinglish &#8212; sab samajhta hun.</div>'
        + '<div class="sg">'
        + '<div class="sc" data-q="Python mein inheritance kya hota hai"><strong>&#128187; Code</strong>Python inheritance explain karo</div>'
        + '<div class="sc" data-q="Taj Mahal ki image dikhao"><strong>&#128444; Image</strong>Taj Mahal dikhao</div>'
        + '<div class="sc" data-q="Aaj ka weather kaisa hai"><strong>&#128172; Baat</strong>Koi bhi sawaal poochho</div>'
        + '<div class="sc" data-q="Mujhe motivate karo"><strong>&#10024; Motivation</strong>Motivational quote do</div>'
        + '</div>';
}

function doClear(){
    mc = 0;
    ch.innerHTML = '';
    var w = document.createElement('div');
    w.id = 'wl';
    w.innerHTML = welHTML();
    ch.appendChild(w);
    document.getElementById('cl').textContent = 'New conversation';
    setSt('Ready');
    fetch('/clear', { method: 'POST' }).catch(function(){});
}

function doSend(){
    var msg = ti.value.trim();
    if(!msg){ return; }
    addUser(msg);
    ti.value = '';
    ti.style.height = '26px';
    ti.style.overflowY = 'hidden';
    addTyping();
    setSt('Thinking...');

    fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
    })
    .then(function(r){
        if(!r.ok){ return r.json().catch(function(){ return {error: 'Server error ' + r.status}; }); }
        return r.json();
    })
    .then(function(d){
        if(d.error){
            var tr = document.getElementById('tr');
            if(tr){ tr.remove(); }
            addAI('⚠️ Error: ' + d.error);
            setSt('Error');
            if(isTM){ startL(); }
            return;
        }
        if(d.type === 'image'){
            if(d.image_url){ addImg(d.image_url, d.query || ''); }
            else { addAI('Image nahi mili: ' + (d.query || '')); }
            setSt('Ready');
            if(isTM){ startL(); }
            return;
        }
        var rep = d.reply || '';
        if(!rep){
            var tr = document.getElementById('tr');
            if(tr){ tr.remove(); }
            addAI('⚠️ Koi response nahi mila. Dobara try karo.');
            setSt('Ready');
            if(isTM){ startL(); }
            return;
        }

        setSt('Typing...');

        // Robot typewriter — audio plays AFTER typing done
        addAI(rep, function(){
            setSt('Ready');
            if(d.audio){
                if(curAud){ curAud.pause(); curAud = null; }
                safeCan();
                var au = new Audio('data:audio/mp3;base64,' + d.audio);
                curAud = au;
                setSt('Speaking...');
                au.onended = function(){ curAud = null; setSt('Ready'); if(isTM){ startL(); } };
                au.onerror = function(){ curAud = null; spk(rep, function(){ if(isTM){ startL(); } }); };
                au.play().catch(function(){ spk(rep, function(){ if(isTM){ startL(); } }); });
            } else {
                spk(rep, function(){ if(isTM){ startL(); } });
            }
        });
    })
    .catch(function(e){
        var tr = document.getElementById('tr');
        if(tr){ tr.remove(); }
        addAI('⚠️ Network Error: ' + e.message);
        setSt('Error');
        if(isTM){ startL(); }
    });
}

function spk(text, onEnd){
    if(!text || !window.speechSynthesis){
        if(onEnd){ onEnd(); }
        return;
    }
    safeCan();

    var clean = '';
    var i = 0;
    while(i < text.length){
        var ci = text.indexOf('```', i);
        if(ci === -1){ clean += text.slice(i); break; }
        if(ci > i){ clean += text.slice(i, ci); }
        var ce = text.indexOf('```', ci + 3);
        if(ce === -1){ break; }
        clean += ' code block. ';
        i = ce + 3;
    }
    clean = clean.split('**').join('').split('`').join('').trim();
    if(!clean){ if(onEnd){ onEnd(); } return; }

    var words = clean.split(' ');
    var chunks = [];
    var cur = '';
    for(var w = 0; w < words.length; w++){
        var candidate = cur ? cur + ' ' + words[w] : words[w];
        if(candidate.length > 150){
            if(cur){ chunks.push(cur); }
            cur = words[w];
        } else {
            cur = candidate;
        }
    }
    if(cur){ chunks.push(cur); }
    if(!chunks.length){ if(onEnd){ onEnd(); } return; }

    var voices = window.speechSynthesis.getVoices();
    var idx = 0;

    var ka = setInterval(function(){
        if(!window.speechSynthesis || !window.speechSynthesis.speaking){
            clearInterval(ka);
            return;
        }
        window.speechSynthesis.pause();
        window.speechSynthesis.resume();
    }, 10000);

    function speakNext(){
        if(idx >= chunks.length){
            clearInterval(ka);
            setSt('Ready');
            if(onEnd){ onEnd(); }
            return;
        }
        var u = new SpeechSynthesisUtterance(chunks[idx]);
        idx++;
        var isH = false;
        for(var c = 0; c < u.text.length; c++){
            var code = u.text.charCodeAt(c);
            if(code >= 0x0900 && code <= 0x097F){ isH = true; break; }
        }
        var v = null;
        for(var vi = 0; vi < voices.length; vi++){
            if(isH && voices[vi].lang.slice(0,2) === 'hi'){ v = voices[vi]; break; }
            if(!isH && voices[vi].lang === 'en-IN'){ v = voices[vi]; break; }
        }
        if(!v){
            for(var vi2 = 0; vi2 < voices.length; vi2++){
                if(voices[vi2].lang.slice(0,2) === 'en'){ v = voices[vi2]; break; }
            }
        }
        if(v){ u.voice = v; }
        u.lang = isH ? 'hi-IN' : 'en-IN';
        u.rate = 0.82; u.pitch = 1.08; u.volume = 1.0;
        u.onend = speakNext;
        u.onerror = function(){ clearInterval(ka); setSt('Ready'); if(onEnd){ onEnd(); } };
        window.speechSynthesis.speak(u);
    }

    setSt('Speaking...');
    speakNext();
}

if(window.speechSynthesis && window.speechSynthesis.onvoiceschanged !== undefined){
    window.speechSynthesis.onvoiceschanged = function(){
        window.speechSynthesis.getVoices();
    };
}

function doToggleTalk(){
    isTM = !isTM;
    if(isTM){
        tkb.textContent = 'Stop';
        tkb.classList.add('on');
        setSt('Talk Mode ON');
        startL();
    } else {
        tkb.textContent = 'Talk';
        tkb.classList.remove('on');
        stopL();
        safeCan();
        if(curAud){ curAud.pause(); curAud = null; }
        setSt('Ready');
    }
}

function bldRec(){
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!SR){ alert('Chrome use karein mic ke liye!'); return null; }
    var r = new SR();
    r.lang = 'hi-IN';
    r.interimResults = false;
    r.maxAlternatives = 1;
    r.onstart  = function(){ isL = true; mb.classList.add('on'); setSt('Listening...'); };
    r.onresult = function(e){ ti.value = e.results[0][0].transcript; stopL(); doSend(); };
    r.onerror  = function(e){ stopL(); setSt('Mic error: ' + e.error); };
    r.onend    = function(){ stopL(); };
    return r;
}

function startL(){
    if(isL){ return; }
    safeCan();
    if(curAud){ curAud.pause(); curAud = null; }
    rec = bldRec();
    if(!rec){ return; }
    try { rec.start(); } catch(e){ console.warn(e); }
}

function stopL(){
    isL = false;
    mb.classList.remove('on');
    if(rec){
        try { rec.stop(); } catch(e){}
        rec = null;
    }
}
