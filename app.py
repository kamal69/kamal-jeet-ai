import os
import json
import re
import base64
import urllib.parse
import urllib.request
import requests
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

app = Flask(__name__)

# API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

groq = Groq(api_key=GROQ_API_KEY)
eleven = ElevenLabs(api_key=ELEVEN_API_KEY)

history = []

SYSTEM = """
You are Sarthi AI.
Reply in the same language user uses.
If user asks for image reply exactly: [IMAGE:query]
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
    return jsonify({"status":"cleared"})

@app.route("/chat", methods=["POST"])
def chat():

    global history

    data = request.json
    msg = data.get("message","")

    history.append({"role":"user","content":msg})
    history = history[-10:]

    messages = [{"role":"system","content":SYSTEM}] + history

    # Tavily internet search
    sr = tavily_search(msg)

    if sr:
        messages.insert(1,{
            "role":"system",
            "content":"Latest internet info:\n\n"+sr
        })

    resp = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=600
    )

    reply = resp.choices[0].message.content.strip()

    history.append({"role":"assistant","content":reply})

    # detect image request
    m = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)

    if m:
        q = m.group(1)

        return jsonify({
            "type":"image",
            "image_url":fetch_image(q),
            "query":q
        })

    return jsonify({
        "reply":reply,
        "audio":tts(reply)
    })


# Tavily Search
def tavily_search(query):

    try:

        url = "https://api.tavily.com/search"

        payload = {
            "api_key":TAVILY_API_KEY,
            "query":query,
            "max_results":5
        }

        r = requests.post(url,json=payload)

        data = r.json()

        results = data.get("results",[])

        text = []

        for item in results[:4]:
            text.append(item["content"])

        return "\n\n".join(text)

    except Exception as e:
        print("Search error:",e)
        return None


# Image fetch
def fetch_image(query):

    try:

        params = urllib.parse.urlencode({
            "key":GOOGLE_API_KEY,
            "cx":GOOGLE_CSE_ID,
            "q":query,
            "searchType":"image",
            "num":1
        })

        url = "https://www.googleapis.com/customsearch/v1?" + params

        req = urllib.request.Request(
            url,
            headers={"User-Agent":"Mozilla/5.0"}
        )

        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())

        items = data.get("items",[])

        if items:
            return items[0]["link"]

    except Exception as e:
        print("Google image error:",e)

    # fallback Unsplash
    q = query.replace(" ","+")
    return f"https://source.unsplash.com/600x400/?{q}"


# Voice
def tts(text):

    try:

        audio = eleven.text_to_speech.convert(
            voice_id="TX3LPaxmHKxFdv7VOQHJ",
            model_id="eleven_turbo_v2_5",
            text=text,
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.35,
                similarity_boost=0.85,
                style=0.45,
                use_speaker_boost=True
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
