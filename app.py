import os, base64, urllib.request, urllib.parse, re, json
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

app = Flask(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID  = os.getenv("GOOGLE_CSE_ID")
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
            voice_id="TX3LPaxmHKxFdv7VOQHJ",    # "Liam" - most natural for multilingual
            model_id="eleven_turbo_v2_5",         # Best model for Hindi/Hinglish naturalness
            text=clean,
            output_format="mp3_44100_128",
            language_code="hi" if has_hindi else "en",
            voice_settings=VoiceSettings(
                stability=0.30,           # Low = very expressive, human-like
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
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return None
    try:
        params = urllib.parse.urlencode({
            "key": GOOGLE_API_KEY,
            "cx":  GOOGLE_CSE_ID,
            "q":   query,
            "num": 5,
            "hl":  "hi",
            "gl":  "in",
            "siteSearch": "www.google.com",
            "siteSearchFilter": "e"   # 'e' = exclude, so searches everywhere EXCEPT restriction
        })
        url = "https://www.googleapis.com/customsearch/v1?" + params
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())

        items = d.get("items", [])
        if not items:
            return None

        parts = []
        for item in items[:4]:
            title   = item.get("title", "")
            snippet = item.get("snippet", "")
            link    = item.get("link", "")
            if snippet:
                parts.append(f"{title}: {snippet} (Source: {link})")

        result = "\n\n".join(parts)
        print(f"Google Search OK — {len(items)} results for: {query}")
        return result

    except Exception as e:
        print("Google Search ERROR: " + str(e))
        return None


def fetch_image(query):
    if GOOGLE_API_KEY and GOOGLE_CSE_ID:
        try:
            params = urllib.parse.urlencode({
                "key":        GOOGLE_API_KEY,
                "cx":         GOOGLE_CSE_ID,
                "q":          query,
                "searchType": "image",
                "num":        1,
                "safe":       "active",
                "gl":         "in",
                "siteSearch": "www.google.com",
                "siteSearchFilter": "e"
            })
            url = "https://www.googleapis.com/customsearch/v1?" + params
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                d = json.loads(r.read().decode())
            items = d.get("items", [])
            if items:
                img_url = items[0].get("link", "")
                if img_url:
                    print(f"Google Image OK: {img_url}")
                    return img_url
        except Exception as e:
            print("Google Image ERROR: " + str(e))

    # Fallback: Wikipedia
    try:
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": query,
            "prop": "pageimages", "pithumbsize": 600, "format": "json"
        })
        with urllib.request.urlopen(url, timeout=6) as r:
            d = json.loads(r.read().decode())
        for page in d["query"]["pages"].values():
            if "thumbnail" in page:
                return page["thumbnail"]["source"]
    except Exception as e:
        print("Wikipedia Image ERROR: " + str(e))

    return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
