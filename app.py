import os, urllib.request, urllib.parse, re, json
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq
from duckduckgo_search import DDGS

load_dotenv()

app = Flask(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

history = []

SYSTEM = """
You are Sarthi AI, a friendly assistant.
Reply in the same language the user uses.
For image requests reply ONLY: [IMAGE:query]
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

    history.append({"role": "user", "content": msg})
    history = history[-10:]

    messages = [{"role": "system", "content": SYSTEM}] + history

    # DuckDuckGo search
    sr = ddg_search(msg)

    if sr:
        messages.insert(1,{
            "role":"system",
            "content":"Latest internet information:\n\n"+sr
        })

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=600,
        temperature=0.8
    )

    reply = resp.choices[0].message.content.strip()

    history.append({"role": "assistant", "content": reply})

    m = re.match(r'^\[IMAGE:(.*?)\]$', reply, re.IGNORECASE)

    if m:
        q = m.group(1)
        return jsonify({
            "type":"image",
            "image_url": fetch_image(q),
            "query":q
        })

    return jsonify({"reply": reply})


# DuckDuckGo search
def ddg_search(query):

    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)

        text = []
        for r in results:
            text.append(r["body"])

        return "\n\n".join(text)

    except Exception as e:
        print("DuckDuckGo error:",e)
        return None


# Google image fetch
def fetch_image(query):

    try:

        params = urllib.parse.urlencode({
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CSE_ID,
            "q": query,
            "searchType": "image",
            "num": 1
        })

        url = "https://www.googleapis.com/customsearch/v1?" + params

        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read().decode())

        items = data.get("items",[])

        if items:
            return items[0].get("link")

    except:
        pass

    return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
