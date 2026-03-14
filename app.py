import os
import requests
import base64
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

groq = Groq(api_key=GROQ_API_KEY)
eleven = ElevenLabs(api_key=ELEVEN_API_KEY)

history = []

@app.route("/")
def home():
    return send_from_directory("templates", "index.html")

@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.json
        msg = data.get("message","")

        history.append({"role":"user","content":msg})

        search_data = tavily_search(msg)

        messages = [
            {"role":"system","content":"Use latest internet info"},
            {"role":"system","content":search_data}
        ] + history

        resp = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )

        reply = resp.choices[0].message.content

        history.append({"role":"assistant","content":reply})

        return jsonify({
            "reply": reply,
            "audio": voice(reply)
        })

    except Exception as e:

        print(e)

        return jsonify({"error": str(e)})


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

        text = ""

        for item in data.get("results",[]):
            text += item["content"] + "\n\n"

        return text

    except:

        return ""


def voice(text):

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

    except:

        return None


if __name__ == "__main__":

    port = int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0",port=port)
