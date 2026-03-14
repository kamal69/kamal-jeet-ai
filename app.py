import os, base64, urllib.request, urllib.parse, re, json
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs

load_dotenv()

app = Flask(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
history = []

SYSTEM = (
    "You are Sarthi AI, a friendly and intelligent assistant created by Kamal Jeet — "
    "a passionate developer from Kullu, Himachal Pradesh who completed his MCA and built "
    "this AI tool for learning and innovation purposes. "
    "You understand Hindi, English, and Hinglish fluently. "
    "VERY IMPORTANT: Reply in the SAME language the user uses — if they write in Hindi/Hinglish, reply in Hindi/Hinglish. "
    "Be conversational, warm, and detailed in your answers — like a knowledgeable friend explaining things. "
    "Do NOT give one-line robotic answers. Explain with examples, context, and a friendly tone. "
    "Use natural flowing sentences, not bullet points unless specifically helpful. "
    "If someone asks who made you or about your creator, say: "
    "'Mujhe Kamal Jeet ne banaya hai, jo Kullu, Himachal Pradesh se hain. "
    "Unhone MCA kiya hai aur yeh project learning aur innovation ke liye banaya hai.' "
    "For image requests reply ONLY with this exact format: [IMAGE:query]"
)


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
    messages = [{"role": "system", "content": SYSTEM}] + history

    sr = web_search(msg)
    if sr:
        messages.insert(1, {"role": "system", "content": "Web info:\n" + sr})

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=600,
        temperature=0.85
    )
    reply = resp.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    m = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
    if m:
        q = m.group(1)
        return jsonify({"type": "image", "image_url": fetch_image(q), "query": q})

    return jsonify({"reply": reply, "audio": eleven_tts(reply)})


def eleven_tts(text):
    try:
        clean = text
        while '```' in clean:
            s = clean.find('```')
            e = clean.find('```', s + 3)
            if e == -1: break
            clean = clean[:s] + ' code block. ' + clean[e+3:]
        clean = clean.replace('**', '').replace('`', '').strip()
        if not clean: return None
        ag = eleven.text_to_speech.convert(
            voice_id="EXAVITQu4vr4xnSDxMaL",   # "Bella" - warm natural female voice
            model_id="eleven_multilingual_v2",
            text=clean,
            output_format="mp3_44100_128",
            voice_settings={
                "stability": 0.4,          # Lower = more expressive, less robotic
                "similarity_boost": 0.75,
                "style": 0.35,             # Adds personality/emotion
                "use_speaker_boost": True
            }
        )
        ab = b"".join(ag)
        if not ab: return None
        print("ElevenLabs OK -- " + str(len(ab)) + " bytes")
        return base64.b64encode(ab).decode()
    except Exception as e:
        print("ElevenLabs ERROR: " + str(e))
        return None


def web_search(query):
    if not TAVILY_API_KEY: return None
    try:
        payload = json.dumps({
            "api_key": TAVILY_API_KEY, "query": query, "max_results": 3
        }).encode()
        req = urllib.request.Request(
            "https://api.tavily.com/search", data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
        if d.get("answer"): return d["answer"]
        return " ".join([x.get("content", "")[:200] for x in d.get("results", [])])
    except Exception as e:
        print("Search error: " + str(e))
        return None


def fetch_image(query):
    try:
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": query,
            "prop": "pageimages", "pithumbsize": 600, "format": "json"
        })
        with urllib.request.urlopen(url) as r:
            d = json.loads(r.read().decode())
        for page in d["query"]["pages"].values():
            if "thumbnail" in page: return page["thumbnail"]["source"]
    except: pass
    return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
