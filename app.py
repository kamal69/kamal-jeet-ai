import os
import requests
import json
import base64
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

app = Flask(__name__)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

groq = Groq(api_key=GROQ_API_KEY)
eleven = ElevenLabs(api_key=ELEVEN_API_KEY)

history = []

SYSTEM = """
You are Sarthi AI.
Always use latest internet information provided.
Reply in same language as user.
"""

@app.route("/")
def home():
    return send_from_directory("templates", "index.html")

@app.route("/chat", methods=["POST"])
def chat():

    global history

    data = request.json
    msg = data.get("message","")

    # Step 1: Internet search
    search_data = tavily_search(msg)

    history.append({"role":"user","content":msg})
    history = history[-10:]

    messages = [
        {"role":"system","content":SYSTEM},
        {"role":"system","content":"Latest internet data:\n"+search_data}
    ] + history

    # Step 2: AI reasoning
    resp = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=600
    )

    reply = resp.choices[0].message.content.strip()

    history.append({"role":"assistant","content":reply})

    return jsonify({
        "reply": reply,
        "audio": tts(reply)
    })


# Tavily search
def tavily_search(query):

    try:

        url = "https://api.tavily.com/search"

        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "max_results": 5
        }

        r = requests.post(url,json=payload)
        data = r.json()

        results = data.get("results",[])

        text = []

        for item in results:
            text.append(item["content"])

        return "\n\n".join(text)

    except Exception as e:
        print("Search error:",e)
        return ""


# Voice output
def tts(text):

    try:

        audio = eleven.text_to_speech.convert(
            voice_id="TX3LPaxmHKxFdv7VOQHJ",
            model_id="eleven_turbo_v2_5",
            text=text,
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.35,
                similarity_boost=0.85
            )
        )

        audio_bytes = b"".join(audio)

        return base64.b64encode(audio_bytes).decode()

    except Exception as e:
        print("Voice error:",e)
        return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
