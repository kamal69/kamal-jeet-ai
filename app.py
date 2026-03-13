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
You are KJ Master AI - a friendly, smart AI assistant.
You understand Hindi, English and Hinglish fluently.
Always reply in the same language the user speaks.
Keep replies short and natural for voice conversation. Max 2-3 sentences.
"""

# ================= HTML (same as your original, only script part changed for better audio handling) =================
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sarthi AI</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<!-- Your full original CSS remains here - no change needed -->
<style>
/* ... your entire CSS ... (copy-paste your original <style> block here) ... */
</style>
</head>
<body>
<!-- Your full HTML body remains here - sidebar, main, chat, input-area etc. -->
<!-- ... paste your original HTML body content ... -->

<script>
// Your original JS functions remain, only send() and audio play part changed

// ... your original functions: autoResize, handleKey, suggest, newChat, clearChat, esc, renderText, copyCode, removeWelcome, addUserMsg, addAiMsg, addTyping, addImageMsg, scrollBottom, speakText, toggleMic, toggleTalk, buildRecognition, startListening, stopListening ...

async function send(){
  const input = document.getElementById('text');
  const msg = input.value.trim(); if(!msg) return;
  addUserMsg(msg);
  input.value=''; input.style.height='auto';
  addTyping();
  setStatus('⏳ Thinking…');
  try{
    const res = await fetch('/chat',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:msg})
    });
    const data = await res.json();
    if(data.type==='image'){
      if(data.image_url) addImageMsg(data.image_url, data.query);
      else addAiMsg('❌ Image nahi mili: '+data.query);
      setStatus('Ready');
      if(isTalkMode) startListening();
      return;
    }
    addAiMsg(data.reply);

    // Improved audio handling
    if(data.audio){
      const audio = new Audio('data:audio/mp3;base64,' + data.audio);
      audio.play()
        .then(() => {
          console.log("ElevenLabs voice played OK");
          setStatus('🔊 Speaking…');
        })
        .catch(err => {
          console.error("ElevenLabs play failed:", err);
          // Fallback to browser TTS
          speakText(data.reply);
          setStatus('🔊 Browser voice (fallback)');
        });
      audio.onended = () => setStatus('Ready');
    } else if(data.reply){
      // If no ElevenLabs audio, use browser TTS
      speakText(data.reply);
    }
  } catch(e){
    const t = document.getElementById('typing'); if(t) t.remove();
    addAiMsg('❌ Error: '+e.message);
    setStatus('Error');
    if(isTalkMode) startListening();
  }
}

// ... rest of your script unchanged ...
</script>
</body>
</html>
"""

# ================= ELEVENLABS VOICE =================
def eleven_tts(text):
    try:
        # Short text only for voice stability
        if len(text) > 400:
            text = text[:380] + "..."

        # Good natural Hindi voices (2026 popular ones - dashboard se confirm kar lo)
        # Options: "Niraj" romantic smooth, "Monika Sogam" calm natural, "Devi" motivating, "Raju" warm clear
        # Yeh ID example hai - actual ID dashboard se copy karo (voice library mein search "Hindi")
        voice_id = "IvLWq57RKibBrqZGpQrC"  # Example: Leo - Energetic Hindi (change as per your account)

        audio_stream = eleven.text_to_speech.convert(
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            text=text,
            output_format="mp3_22050_64"   # Low size, fast loading
        )

        audio_bytes = b"".join(audio_stream)
        return base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        print("ElevenLabs ERROR:", str(e))
        return None

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/clear", methods=["POST"])
def clear():
    global history
    history = []
    return jsonify({"status":"cleared"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message","")
    history.append({"role":"user", "content":msg})

    messages = [{"role":"system","content":SYSTEM}] + history

    search = web_search(msg)  # your original function
    if search:
        messages.insert(1, {"role":"system", "content":"Latest web info:\n"+search})

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=300,
        temperature=0.7
    )

    reply = resp.choices[0].message.content.strip()
    history.append({"role":"assistant", "content":reply})

    img_match = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
    if img_match:
        q = img_match.group(1)
        img = fetch_image(q)
        return jsonify({"type":"image", "image_url":img, "query":q})

    audio_b64 = eleven_tts(reply)
    return jsonify({
        "reply": reply,
        "audio": audio_b64   # can be None if failed
    })

# Your other functions: web_search, fetch_image remain same

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)  # debug=True for better error visibility