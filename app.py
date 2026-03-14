import os, base64, urllib.request, urllib.parse, re, json
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
history = []

SYSTEM = (
    "You are Sarthi AI, a friendly and intelligent assistant. "
    "You understand Hindi, English, and Hinglish fluently. "
    "VERY IMPORTANT: Reply in the SAME language the user uses. "
    "If user writes Hinglish (mix of Hindi+English), reply in natural casual Hinglish. "
    "If user writes pure Hindi, reply in simple everyday Hindi — avoid heavy Sanskrit words like 'sthit', 'smaarak', 'nirman'. "
    "Use simple words: 'hai' not 'hain', 'banaya' not 'nirmit kiya', 'mein' not 'mein sthit'. "
    "Be like a knowledgeable dost — warm, natural, detailed with examples. "
    "Do NOT give one-line answers. Give good explanation naturally. "
    "OWNER INFO — Only share if directly asked 'who made you', 'kisne banaya', 'owner kaun hai': "
    "Mujhe Kamal Jeet ne banaya hai jo Kullu, Himachal Pradesh se hain, "
    "unhone MCA ki hai aur yeh project learning aur innovation ke liye banaya hai. "
    "DO NOT mention owner info unless directly asked. "
    "For image requests reply ONLY: [IMAGE:query]"
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
        messages.insert(1, {
            "role": "system",
            "content": (
                "Yeh Google Search se real-time information mili hai, isse use karo apne jawab mein:\n\n"
                + sr +
                "\n\nIn results ke basis pe accurate aur detailed jawab do."
            )
        })

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

        # Detect if text has Hindi characters
        has_hindi = any('\u0900' <= ch <= '\u097F' for ch in clean)

        ag = eleven.text_to_speech.convert(
            voice_id="TX3LPaxmHKxFdv7VOQHJ",
            model_id="eleven_turbo_v2_5",
            text=clean,
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.30,
                similarity_boost=0.75,
                style=0.45,
                use_speaker_boost=True
            )
        )
        ab = b"".join(ag)
        if not ab: return None
        print("ElevenLabs OK -- " + str(len(ab)) + " bytes")
        return base64.b64encode(ab).decode()
    except Exception as e:
        print("ElevenLabs ERROR: " + str(e))
        return None


def web_search(query):
    try:
        # DuckDuckGo Instant Answer API - completely free, no key needed
        params = urllib.parse.urlencode({
            "q":              query,
            "format":         "json",
            "no_html":        "1",
            "skip_disambig":  "1"
        })
        url = "https://api.duckduckgo.com/?" + params
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 SarthiAI/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())

        parts = []

        # Abstract (Wikipedia-style summary)
        if d.get("AbstractText"):
            parts.append(d["AbstractText"])

        # Related topics
        for topic in d.get("RelatedTopics", [])[:4]:
            text = topic.get("Text", "")
            if text:
                parts.append(text)

        # Answer (for simple queries like math, dates)
        if d.get("Answer"):
            parts.insert(0, d["Answer"])

        if parts:
            result = "\n\n".join(parts[:5])
            print(f"DuckDuckGo Search OK for: {query}")
            return result

        print(f"DuckDuckGo: no results for: {query}")
        return None

    except Exception as e:
        print("DuckDuckGo Search ERROR: " + str(e))
        return None


def fetch_image(query):
    # DuckDuckGo image search
    try:
        params = urllib.parse.urlencode({
            "q":      query,
            "format": "json",
            "iax":    "images",
            "ia":     "images"
        })
        url = "https://api.duckduckgo.com/?" + params
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 SarthiAI/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())

        # Try thumbnail from main result
        if d.get("Image"):
            img = d["Image"]
            if img.startswith("http"):
                print(f"DuckDuckGo Image OK: {img}")
                return img

        # Try from related topics
        for topic in d.get("RelatedTopics", []):
            icon = topic.get("Icon", {})
            url_img = icon.get("URL", "")
            if url_img and url_img.startswith("http"):
                print(f"DDG Topic Image OK: {url_img}")
                return url_img

    except Exception as e:
        print("DuckDuckGo Image ERROR: " + str(e))

    # Fallback: Wikipedia
    try:
        wiki_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action":      "query",
            "titles":      query,
            "prop":        "pageimages",
            "pithumbsize": 600,
            "format":      "json"
        })
        req = urllib.request.Request(
            wiki_url,
            headers={"User-Agent": "Mozilla/5.0 SarthiAI/1.0"}
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            d = json.loads(r.read().decode())
        for page in d["query"]["pages"].values():
            if "thumbnail" in page:
                print(f"Wikipedia Image OK: {page['thumbnail']['source']}")
                return page["thumbnail"]["source"]
    except Exception as e:
        print("Wikipedia Image ERROR: " + str(e))

    return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
