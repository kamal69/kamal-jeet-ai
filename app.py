import os
import json
import re
import base64
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
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

groq = Groq(api_key=GROQ_API_KEY)
eleven = ElevenLabs(api_key=ELEVEN_API_KEY)

history = []

SYSTEM = """
You are Sarthi AI, a helpful assistant.
Reply in the same language user uses.
If user asks for latest news or search results, show structured results.
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

    # detect news/search request
    if "news" in msg.lower() or "latest" in msg.lower():
        news = tavily_news(msg)

        return jsonify({
            "type": "news",
            "results": news
        })

    history.append({"role": "user", "content": msg})
    history = history[-10:]

    messages = [{"role": "system", "content": SYSTEM}] + history

    resp = groq.chat.completions.create(
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


# Tavily news search
def tavily_news(query):

    try:

        url = "https://api.tavily.com/search"

        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "include_images": True,
            "max_results": 5
        }

        r = requests.post(url, json=payload)

        data = r.json()

        results = []

        for item in data.get("results", []):

            results.append({
                "title": item.get("title"),
                "content": item.get("content"),
                "url": item.get("url"),
                "image": item.get("image")
            })

        return results

    except Exception as e:
        print("Search error:", e)
        return []


# ElevenLabs voice
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
        print("Voice error:", e)
        return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
