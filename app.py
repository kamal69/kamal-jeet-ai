import os, base64, urllib.request, urllib.parse, re, json
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)

# 🔑 KEYS
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID  = os.getenv("GOOGLE_CSE_ID")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

history = []
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🧠 SYSTEM PROMPT
SYSTEM = (
    "You are Sarthi AI, a friendly and intelligent assistant. "
    "You understand Hindi, English, and Hinglish fluently. "
    "Reply in SAME language as user. "
    "Be natural, like a dost. Give detailed answers. "
    "For image requests reply ONLY: [IMAGE:query]"
)

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

@app.route("/chat", methods=["POST"])
def chat():
    global history
    try:
        data = request.json
        msg = data.get("message", "").strip()

        if not msg:
            return jsonify({"error": "Empty message"}), 400

        history.append({"role": "user", "content": msg})

        # 🔍 Google Search
        sr = web_search(msg)

        # 🧠 Prompt Build (Gemini style)
        prompt = SYSTEM + "\n\n"

        if sr:
            prompt += "Real-time info:\n" + sr + "\n\n"

        for h in history:
            prompt += f"{h['role'].upper()}: {h['content']}\n"

        # 🚀 Gemini Response
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(prompt)

        reply = response.text.strip() if response.text else "Kuch issue aaya, dobara try karo."

        history.append({"role": "assistant", "content": reply})

        # 🖼️ Image detection
        m = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
        if m:
            q = m.group(1)
            return jsonify({
                "type": "image",
                "image_url": fetch_image(q),
                "query": q
            })

        return jsonify({
            "reply": reply,
            "audio": eleven_tts(reply)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🔊 ElevenLabs TTS
def eleven_tts(text):
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings

        eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

        clean = text.replace('**', '').replace('`', '').strip()
        if not clean:
            return None

        ag = eleven.text_to_speech.convert(
            voice_id="zT03pEAEi0VHKciJODfn",
            model_id="eleven_multilingual_v2",
            text=clean,
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.85,
                style=0.2,
                use_speaker_boost=True
            )
        )

        ab = b"".join(ag)
        return base64.b64encode(ab).decode()

    except Exception as e:
        print("TTS ERROR:", e)
        return None


# 🔍 Google Search
def web_search(query):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return None

    try:
        params = urllib.parse.urlencode({
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CSE_ID,
            "q": query,
            "num": 3
        })

        url = "https://www.googleapis.com/customsearch/v1?" + params
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read().decode())

        results = []
        for item in data.get("items", []):
            results.append(item.get("snippet", ""))

        return "\n".join(results)

    except:
        return None


# 🖼️ Image Fetch
def fetch_image(query):
    try:
        url = "https://source.unsplash.com/600x400/?" + urllib.parse.quote(query)
        return url
    except:
        return None


if __name__ == "__main__":
    app.run(debug=True)
