import os
import base64
import urllib.request
import urllib.parse
import re
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)

# ============================================================
# 🔑 API KEYS
# ============================================================
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID   = os.getenv("GOOGLE_CSE_ID")
ELEVEN_API_KEY  = os.getenv("ELEVEN_API_KEY")
TAVILY_API_KEY  = os.getenv("TAVILY_API_KEY")

# ============================================================
# 🤖 GROQ CLIENT  (replaces Gemini — free & fast)
# ============================================================
groq_client = Groq(api_key=GROQ_API_KEY)

history = []
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 🧠 SYSTEM PROMPT
# ============================================================
SYSTEM = (
    "You are Sarthi AI, a friendly and intelligent assistant. "
    "You understand Hindi, English, and Hinglish fluently. "
    "Reply in the SAME language as the user. "
    "Be natural, helpful, like a dost. Give detailed answers. "
    "When user asks for an image or picture, reply ONLY with: [IMAGE:search_query] "
    "When user asks you to write or explain code, wrap code in proper markdown code blocks. "
    "Never break character."
)

# ============================================================
# 🌐 ROUTES
# ============================================================
@app.route("/")
def home():
    tmpl = os.path.join(BASE_DIR, "templates")
    if os.path.isfile(os.path.join(tmpl, "index.html")):
        return send_from_directory(tmpl, "index.html")
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)

@app.route("/clear", methods=["POST"])
def clear():
    global history
    history = []
    return jsonify({"status": "cleared"})


# ============================================================
# 💬 MAIN CHAT ROUTE
# ============================================================
@app.route("/chat", methods=["POST"])
def chat():
    global history
    try:
        data   = request.json
        msg    = data.get("message", "").strip()
        image  = data.get("image", None)   # base64 image from frontend (optional)

        if not msg and not image:
            return jsonify({"error": "Empty message"}), 400

        # ── Build user content ──────────────────────────────
        if image:
            # Image understanding via Groq vision model
            user_content = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image}"
                    }
                },
                {
                    "type": "text",
                    "text": msg if msg else "Is image mein kya hai? Detail mein batao."
                }
            ]
        else:
            user_content = msg

        history.append({"role": "user", "content": user_content if image else msg})

        # ── Web search (Tavily preferred, Google fallback) ──
        search_context = ""
        if not image:
            search_context = tavily_search(msg) or google_search(msg) or ""

        # ── Build messages for Groq ──────────────────────────
        messages = [{"role": "system", "content": SYSTEM}]

        if search_context:
            messages.append({
                "role": "system",
                "content": f"Real-time web info:\n{search_context}"
            })

        # Add history (last 10 turns to avoid token overflow)
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})

        # ── Groq API Call ────────────────────────────────────
        model = (
            "llama-3.2-11b-vision-preview"   # vision model for images
            if image else
            "llama-3.3-70b-versatile"        # best free text model
        )

        response = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )

        reply = response.choices[0].message.content.strip()

        history.append({"role": "assistant", "content": reply})

        # ── Image request detection ──────────────────────────
        img_match = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
        if img_match:
            query     = img_match.group(1)
            image_url = fetch_image(query)
            return jsonify({
                "type":      "image",
                "image_url": image_url,
                "query":     query
            })

        # ── Code block detection ─────────────────────────────
        has_code = bool(re.search(r'```[\w]*\n', reply))

        # ── TTS (voice) ──────────────────────────────────────
        # Don't read out giant code blocks — only clean text
        audio_b64 = None
        if not has_code:
            tts_text  = re.sub(r'```[\s\S]*?```', '', reply).strip()
            audio_b64 = eleven_tts(tts_text)

        return jsonify({
            "reply":    reply,
            "audio":    audio_b64,
            "has_code": has_code
        })

    except Exception as e:
        print("CHAT ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ============================================================
# 🔊 ELEVENLABS TTS  (fixed + robust)
# ============================================================
def eleven_tts(text):
    if not ELEVEN_API_KEY:
        return None
    try:
        # Trim — ElevenLabs free tier has char limit
        text = text[:500].strip()
        if not text:
            return None

        # Strip markdown symbols so voice sounds natural
        clean = re.sub(r'[*_`#>~\[\]()]', '', text).strip()
        if not clean:
            return None

        url = "https://api.elevenlabs.io/v1/text-to-speech/zT03pEAEi0VHKciJODfn"
        headers = {
            "xi-api-key":   ELEVEN_API_KEY,
            "Content-Type": "application/json",
            "Accept":       "audio/mpeg"
        }
        payload = {
            "text":       clean,
            "model_id":   "eleven_multilingual_v2",
            "voice_settings": {
                "stability":         0.5,
                "similarity_boost":  0.85,
                "style":             0.2,
                "use_speaker_boost": True
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=15)

        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode()
        else:
            print("TTS HTTP ERROR:", resp.status_code, resp.text[:200])
            return None

    except Exception as e:
        print("TTS ERROR:", e)
        return None


# ============================================================
# 🔍 TAVILY SEARCH  (best AI search, free tier available)
# ============================================================
def tavily_search(query):
    if not TAVILY_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key":        TAVILY_API_KEY,
                "query":          query,
                "search_depth":   "basic",
                "max_results":    3,
                "include_answer": True
            },
            timeout=8
        )
        if resp.status_code == 200:
            data     = resp.json()
            answer   = data.get("answer", "")
            results  = data.get("results", [])
            snippets = [r.get("content", "") for r in results[:3]]
            combined = (answer + "\n" + "\n".join(snippets)).strip()
            return combined[:1500] if combined else None
    except Exception as e:
        print("TAVILY ERROR:", e)
    return None


# ============================================================
# 🔍 GOOGLE SEARCH  (fallback)
# ============================================================
def google_search(query):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return None
    try:
        params = urllib.parse.urlencode({
            "key": GOOGLE_API_KEY,
            "cx":  GOOGLE_CSE_ID,
            "q":   query,
            "num": 3
        })
        url = "https://www.googleapis.com/customsearch/v1?" + params
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read().decode())
        snippets = [item.get("snippet", "") for item in data.get("items", [])]
        return "\n".join(snippets)[:1500]
    except Exception as e:
        print("GOOGLE SEARCH ERROR:", e)
        return None


# ============================================================
# 🖼️ IMAGE FETCH
# ============================================================
def fetch_image(query):
    try:
        return "https://source.unsplash.com/600x400/?" + urllib.parse.quote(query)
    except:
        return None


# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
