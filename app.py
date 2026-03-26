import os
import base64
import urllib.request
import urllib.parse
import re
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)

# ============================================================
# 🔑 API KEYS
# ============================================================
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID   = os.getenv("GOOGLE_CSE_ID")
ELEVEN_API_KEY  = os.getenv("ELEVEN_API_KEY")
TAVILY_API_KEY  = os.getenv("TAVILY_API_KEY")

# ============================================================
# 🤖 GROQ CLIENT  (replaces Gemini — free & fast)
# ============================================================
groq_client = Groq(api_key=GROQ_API_KEY)

history = []
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 🧠 SYSTEM PROMPT
# ============================================================
SYSTEM = (
    "Tu Sarthi hai — Kamal Jeet ka personal AI dost, banaya gaya Himachal Pradesh mein. "
    "Tu ek real insaan ki tarah baat karta hai — bilkul natural, jaise koi purana yaar. "
    "Tu Amazon, Google, Meta ya kisi bhi company ka product NAHI hai. "
    "Agar koi pooche kisne banaya, seedha bol: Mujhe Kamal Jeet bhai ne banaya hai! "
    "BAAT KARNE KA TARIKA: "
    "Seedha baat kar jaise dost karta hai. Haan yaar, Sahi baat hai, Arre nahi bhai — aisa natural feel hona chahiye. "
    "Kabhi bhi robot jaisi formal bhasha mat bol. Certainly, Absolutely, As an AI — yeh sab bilkul mat bol. "
    "Thoda casual, thoda serious — situation ke hisaab se adjust kar. "
    "Agar koi mazak kare tu bhi hasa. Agar koi udas ho tu samjhe usse. "
    "Zyada lambe paragraphs mat likh — thodi thodi baat kar, naturally flow karo. "
    "Hinglish, Hindi, English — jo user bole wahi bol tu bhi. "
    "KHAAS RULES: "
    "Agar image mangein toh sirf [IMAGE:search_query] likh, kuch aur nahi. "
    "Code explain karna ho toh proper markdown code blocks use kar. "
    "Kabhi character mat todo — Tu Sarthi hai, hamesha Sarthi rahega. "
)

# ============================================================
# 🌐 ROUTES
# ============================================================
@app.route("/")
def home():
    tmpl = os.path.join(BASE_DIR, "templates")
    if os.path.isfile(os.path.join(tmpl, "index.html")):
        return send_from_directory(tmpl, "index.html")
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)

@app.route("/clear", methods=["POST"])
def clear():
    global history
    history = []
    return jsonify({"status": "cleared"})


# ============================================================
# 💬 MAIN CHAT ROUTE
# ============================================================
@app.route("/chat", methods=["POST"])
def chat():
    global history
    try:
        data   = request.json
        msg    = data.get("message", "").strip()
        image  = data.get("image", None)   # base64 image from frontend (optional)

        if not msg and not image:
            return jsonify({"error": "Empty message"}), 400

        # ── Build user content ──────────────────────────────
        if image:
            # Image understanding via Groq vision model
            user_content = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image}"
                    }
                },
                {
                    "type": "text",
                    "text": msg if msg else "Is image mein kya hai? Detail mein batao."
                }
            ]
        else:
            user_content = msg

        history.append({"role": "user", "content": user_content if image else msg})

        # ── Web search (Tavily preferred, Google fallback) ──
        search_context = ""
        if not image:
            search_context = tavily_search(msg) or google_search(msg) or ""

        # ── Build messages for Groq ──────────────────────────
        messages = [{"role": "system", "content": SYSTEM}]

        if search_context:
            messages.append({
                "role": "system",
                "content": f"Real-time web info:\n{search_context}"
            })

        # Add history (last 10 turns to avoid token overflow)
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})

        # ── Groq API Call ────────────────────────────────────
        model = (
            "llama-3.2-11b-vision-preview"   # vision model for images
            if image else
            "llama-3.3-70b-versatile"        # best free text model
        )

        response = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )

        reply = response.choices[0].message.content.strip()

        history.append({"role": "assistant", "content": reply})

        # ── Image request detection ──────────────────────────
        img_match = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)
        if img_match:
            query     = img_match.group(1)
            image_url = fetch_image(query)
            return jsonify({
                "type":      "image",
                "image_url": image_url,
                "query":     query
            })

        # ── Code block detection ─────────────────────────────
        has_code = bool(re.search(r'```[\w]*\n', reply))

        # ── TTS (voice) ──────────────────────────────────────
        # Don't read out giant code blocks — only clean text
        audio_b64 = None
        if not has_code:
            tts_text  = re.sub(r'```[\s\S]*?```', '', reply).strip()
            audio_b64 = eleven_tts(tts_text)

        return jsonify({
            "reply":    reply,
            "audio":    audio_b64,
            "has_code": has_code
        })

    except Exception as e:
        print("CHAT ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ============================================================
# 🔊 ELEVENLABS TTS  (fixed + robust)
# ============================================================
def eleven_tts(text):
    if not ELEVEN_API_KEY:
        return None
    try:
        # Trim — ElevenLabs free tier has char limit
        text = text[:500].strip()
        if not text:
            return None

        # Strip markdown symbols so voice sounds natural
        clean = re.sub(r'[*_`#>~\[\]()]', '', text).strip()
        if not clean:
            return None

        url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
        headers = {
            "xi-api-key":   ELEVEN_API_KEY,
            "Content-Type": "application/json",
            "Accept":       "audio/mpeg"
        }
        payload = {
            "text":       clean,
            "model_id":   "eleven_multilingual_v2",
            "voice_settings": {
                "stability":         0.5,
                "similarity_boost":  0.85,
                "style":             0.2,
                "use_speaker_boost": True
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=15)

        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode()
        else:
            print("TTS HTTP ERROR:", resp.status_code, resp.text[:200])
            return None

    except Exception as e:
        print("TTS ERROR:", e)
        return None


# ============================================================
# 🔍 TAVILY SEARCH  (best AI search, free tier available)
# ============================================================
def tavily_search(query):
    if not TAVILY_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key":        TAVILY_API_KEY,
                "query":          query,
                "search_depth":   "basic",
                "max_results":    3,
                "include_answer": True
            },
            timeout=8
        )
        if resp.status_code == 200:
            data     = resp.json()
            answer   = data.get("answer", "")
            results  = data.get("results", [])
            snippets = [r.get("content", "") for r in results[:3]]
            combined = (answer + "\n" + "\n".join(snippets)).strip()
            return combined[:1500] if combined else None
    except Exception as e:
        print("TAVILY ERROR:", e)
    return None


# ============================================================
# 🔍 GOOGLE SEARCH  (fallback)
# ============================================================
def google_search(query):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return None
    try:
        params = urllib.parse.urlencode({
            "key": GOOGLE_API_KEY,
            "cx":  GOOGLE_CSE_ID,
            "q":   query,
            "num": 3
        })
        url = "https://www.googleapis.com/customsearch/v1?" + params
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read().decode())
        snippets = [item.get("snippet", "") for item in data.get("items", [])]
        return "\n".join(snippets)[:1500]
    except Exception as e:
        print("GOOGLE SEARCH ERROR:", e)
        return None


# ============================================================
# 🖼️ IMAGE FETCH  (Multi-method, no extra API key needed)
# ============================================================
def fetch_image(query):

    # Method 1: Wikimedia / Wikipedia thumbnail (FREE, accurate for famous things)
    try:
        search_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action":      "query",
            "titles":      query,
            "prop":        "pageimages",
            "format":      "json",
            "pithumbsize": 600,
            "redirects":   1
        })
        req = urllib.request.Request(search_url, headers={"User-Agent": "SarthiAI/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                print("IMAGE: Wikipedia hit ->", thumb)
                return thumb
    except Exception as e:
        print("WIKIPEDIA ERROR:", e)

    # Method 2: DuckDuckGo instant answer image (FREE, no key)
    try:
        ddg_url = "https://api.duckduckgo.com/?q=" + urllib.parse.quote(query) + "&format=json"
        req = urllib.request.Request(ddg_url, headers={"User-Agent": "SarthiAI/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        image = data.get("Image") or data.get("image")
        if image and str(image).startswith("http"):
            print("IMAGE: DuckDuckGo hit ->", image)
            return image
    except Exception as e:
        print("DDG ERROR:", e)

    # Method 3: Google Custom Search (if keys available)
    if GOOGLE_API_KEY and GOOGLE_CSE_ID:
        try:
            params = urllib.parse.urlencode({
                "key":        GOOGLE_API_KEY,
                "cx":         GOOGLE_CSE_ID,
                "q":          query,
                "searchType": "image",
                "num":        1,
                "safe":       "active"
            })
            url = "https://www.googleapis.com/customsearch/v1?" + params
            with urllib.request.urlopen(url, timeout=8) as r:
                data = json.loads(r.read().decode())
            items = data.get("items", [])
            if items:
                img_url = items[0].get("link")
                print("IMAGE: Google CSE hit ->", img_url)
                return img_url
        except Exception as e:
            print("GOOGLE IMAGE ERROR:", e)

    # Method 4: Lexica AI art (FREE, no key, beautiful images)
    try:
        lex_url = "https://lexica.art/api/v1/search?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(lex_url, headers={"User-Agent": "SarthiAI/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        images = data.get("images", [])
        if images:
            src = images[0].get("src")
            print("IMAGE: Lexica hit ->", src)
            return src
    except Exception as e:
        print("LEXICA ERROR:", e)

    # Method 5: Last resort — Picsum random photo
    seed = abs(hash(query)) % 1000
    return f"https://picsum.photos/seed/{seed}/600/400"


# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
