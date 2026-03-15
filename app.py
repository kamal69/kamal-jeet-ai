import os
import base64
import urllib.request
import urllib.parse
import re
import json

from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs

load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")

GROQ_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_KEY = os.getenv("ELEVEN_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = Groq(api_key=GROQ_KEY)
eleven = ElevenLabs(api_key=ELEVEN_KEY)

history = []

SYSTEM = """
You are KJ Master AI.
Friendly AI assistant.
Speak Hindi, English, Hinglish.
Keep answers short and natural.
"""

# ================= SERVE HTML =================

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/app.js")
def js():
    return send_from_directory(".", "app.js")


# ================= CLEAR CHAT =================

@app.route("/clear", methods=["POST"])
def clear():
    global history
    history = []
    return jsonify({"status": "cleared"})


# ================= WEB SEARCH =================

def web_search(query):

    if not TAVILY_API_KEY:
        return None

    try:

        payload = json.dumps({
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": 3
        }).encode()

        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())

        if data.get("answer"):
            return data["answer"]

        results = data.get("results", [])

        snippets = [r.get("content","")[:200] for r in results]

        return " ".join(snippets)

    except:
        return None


# ================= IMAGE =================

def fetch_image(query):

    try:

        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({

            "action":"query",
            "titles":query,
            "prop":"pageimages",
            "pithumbsize":600,
            "format":"json"

        })

        with urllib.request.urlopen(url) as r:

            data = json.loads(r.read().decode())

        for page in data["query"]["pages"].values():

            if "thumbnail" in page:

                return page["thumbnail"]["source"]

    except:
        pass

    return None


# ================= TTS =================

def eleven_tts(text):

    if not ELEVEN_KEY:
        return None

    try:

        audio = eleven.text_to_speech.convert(

            voice_id="21m00Tcm4TlvDq8ikWAM",

            model_id="eleven_multilingual_v2",

            text=text

        )

        audio_bytes = b"".join(audio)

        return base64.b64encode(audio_bytes).decode()

    except:
        return None


# ================= CHAT =================

@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json()

        msg = data.get("message","")

        history.append({
            "role":"user",
            "content":msg
        })

        messages = [{"role":"system","content":SYSTEM}] + history

        search = web_search(msg)

        if search:

            messages.insert(1,{
                "role":"system",
                "content":"Latest web info:\n"+search
            })

        resp = client.chat.completions.create(

            model="llama-3.3-70b-versatile",

            messages=messages,

            temperature=0.7,
            max_tokens=400
        )

        reply = resp.choices[0].message.content.strip()

        history.append({
            "role":"assistant",
            "content":reply
        })

        img_match = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)

        if img_match:

            q = img_match.group(1)

            img = fetch_image(q)

            return jsonify({

                "type":"image",
                "image_url":img,
                "query":q
            })

        audio = eleven_tts(reply)

        return jsonify({

            "reply":reply,
            "audio":audio
        })

    except Exception as e:

        return jsonify({
            "reply":"Server error: "+str(e)
        })


# ================= RUN =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0", port=port)
