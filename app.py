import os, base64, urllib.request, urllib.parse, re, json
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

app = Flask(__name__)

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

history = []

SYSTEM = """
You are Sarthi AI, a friendly and intelligent assistant.
Reply in same language user uses (Hindi / English / Hinglish).
Give natural explanation like a helpful friend.
For image request reply ONLY: [IMAGE:query]
"""


@app.route("/")
def home():
    return send_from_directory("templates", "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


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

    # Limit memory
    history = history[-10:]

    messages = [{"role": "system", "content": SYSTEM}] + history

    # Real-time search
    sr = tavily_search(msg)

    if not sr:
        sr = google_search(msg)

    if sr:
        messages.insert(1, {
            "role": "system",
            "content": "Real time internet data:\n\n" + sr
        })

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=600,
            temperature=0.85
        )

        reply = resp.choices[0].message.content.strip()

    except Exception as e:
        return jsonify({"reply": "AI service temporarily unavailable."})

    history.append({"role": "assistant", "content": reply})

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


# Tavily Search (NEW)
def tavily_search(query):
    if not TAVILY_API_KEY:
        return None

    try:
        url = "https://api.tavily.com/search"

        payload = json.dumps({
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": 5
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())

        results = data.get("results", [])

        if not results:
            return None

        parts = []
        for item in results[:4]:
            parts.append(item["content"])

        return "\n\n".join(parts)

    except Exception as e:
        print("Tavily ERROR:", e)
        return None


# Google Search fallback
def google_search(query):

    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return None

    try:
        params = urllib.parse.urlencode({
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CSE_ID,
            "q": query,
            "num": 5
        })

        url = "https://www.googleapis.com/customsearch/v1?" + params

        with urllib.request.urlopen(url) as r:
            d = json.loads(r.read().decode())

        items = d.get("items", [])

        parts = []

        for item in items[:4]:
            parts.append(item.get("snippet", ""))

        return "\n\n".join(parts)

    except:
        return None


# Image fetch
def fetch_image(query):

    try:
        params = urllib.parse.urlencode({
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CSE_ID,
            "q": query,
            "searchType": "image",
            "num": 1
        })

        url = "https://www.googleapis.com/customsearch/v1?" + params

        with urllib.request.urlopen(url) as r:
            d = json.loads(r.read().decode())

        items = d.get("items", [])

        if items:
            return items[0].get("link")

    except:
        pass

    return None


# ElevenLabs voice
def eleven_tts(text):

    try:

        ag = eleven.text_to_speech.convert(
            voice_id="TX3LPaxmHKxFdv7VOQHJ",
            model_id="eleven_turbo_v2_5",
            text=text,
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.35,
                similarity_boost=0.75
            )
        )

        ab = b"".join(ag)

        return base64.b64encode(ab).decode()

    except:
        return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
