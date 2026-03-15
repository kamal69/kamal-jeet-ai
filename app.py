import os
import requests
import base64
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()
app = Flask(__name__)

GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
eleven = ElevenLabs(api_key=ELEVEN_API_KEY)

history = []

SYSTEM = """
You are Sarthi AI.
Always use latest internet information provided.
Reply in same language as user.
"""

@app.route("/")
def home():
    return render_template("index.html")   # ✅ Fix 1

@app.route("/clear", methods=["POST"])     # ✅ Fix 2
def clear():
    global history
    history = []
    return jsonify({"status": "cleared"})

@app.route("/chat", methods=["POST"])
def chat():
    global history
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    msg = data.get("message", "")
    if not msg:
        return jsonify({"error": "Empty message"}), 400

    search_data = tavily_search(msg)
    history.append({"role": "user", "content": msg})
    history = history[-10:]

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "system", "content": "Latest internet data:\n" + search_data}
    ] + history

    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=600
    )
    reply = resp.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    return jsonify({
        "reply": reply,
        "audio": tts(reply)
    })

def tavily_search(query):
    try:
        r = requests.post("https://api.tavily.com/search", json={
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "max_results": 5
        })
        results = r.json().get("results", [])
        return "\n\n".join(i["content"] for i in results)
    except Exception as e:
        print("Search error:", e)
        return ""

def tts(text):
    try:
        audio = eleven.text_to_speech.convert(
            voice_id="TX3LPaxmHKxFdv7VOQHJ",
            model_id="eleven_turbo_v2_5",
            text=text,
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(stability=0.35, similarity_boost=0.85)
        )
        return base64.b64encode(b"".join(audio)).decode()
    except Exception as e:
        print("Voice error:", e)
        return None

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
