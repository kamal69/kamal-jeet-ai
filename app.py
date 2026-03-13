import os
import base64
import urllib.request
import urllib.parse
import re
import json

from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY)

history = []

SYSTEM = """
You are KJ Master AI, a helpful AI assistant created by Kamal Jeet.
Always respond naturally in Hindi, English or Hinglish depending on the user language.
Keep responses short and conversational.

If user asks for images return format:
[IMAGE:object]
"""

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>KJ Master AI</title>
<style>
body{background:#111;color:white;font-family:sans-serif}
#chat{height:70vh;overflow:auto;border:1px solid #444;padding:10px}
input{width:80%;padding:10px}
button{padding:10px}
</style>
</head>
<body>

<h2>KJ Master AI</h2>

<div id="chat"></div>

<input id="text" placeholder="Ask anything...">
<button onclick="send()">Send</button>

<script>

function add(msg){
   const div=document.createElement("div")
   div.innerHTML=msg
   document.getElementById("chat").appendChild(div)
}

async function send(){

 const input=document.getElementById("text")
 const msg=input.value

 add("<b>You:</b> "+msg)

 input.value=""

 const res=await fetch("/chat",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({message:msg})
 })

 const data=await res.json()

 if(data.type==="image"){
    add("<img src='"+data.image_url+"' width='300'>")
    return
 }

 add("<b>AI:</b> "+data.reply)

 if(data.audio){
    const audio=new Audio("data:audio/mp3;base64,"+data.audio)
    audio.play()
 }

}

</script>
</body>
</html>
"""

# -----------------------------
# LANGUAGE DETECTION
# -----------------------------

def detect_lang(text):
    hindi_chars = "अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह"
    return "hi" if sum(1 for c in text if c in hindi_chars) > 2 else "en"


# -----------------------------
# WEB SEARCH (TAVILY)
# -----------------------------

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
            headers={"Content-Type":"application/json"}
        )

        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())

        results = data.get("results",[])

        texts=[x["content"][:200] for x in results]

        return " ".join(texts)

    except:
        return None


# -----------------------------
# IMAGE FETCH
# -----------------------------

def fetch_image(query):

    try:

        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action":"query",
            "titles":query,
            "prop":"pageimages",
            "pithumbsize":500,
            "format":"json"
        })

        with urllib.request.urlopen(url) as r:

            data=json.loads(r.read().decode())

        for page in data["query"]["pages"].values():

            if "thumbnail" in page:
                return page["thumbnail"]["source"]

    except:
        pass

    return None


# -----------------------------
# TEXT TO SPEECH
# -----------------------------

def run_tts(text, lang):

    try:

        voice="Arista-PlayAI"

        resp = client.audio.speech.create(
            model="playai-tts",
            voice=voice,
            input=text,
            response_format="mp3"
        )

        audio=resp.read()

        return base64.b64encode(audio).decode()

    except Exception as e:
        print("TTS error",e)
        return None


# -----------------------------
# ROUTES
# -----------------------------

@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/chat",methods=["POST"])
def chat():

    data=request.json
    msg=data.get("message")

    lang=detect_lang(msg)

    history.append({"role":"user","content":msg})

    context=[{"role":"system","content":SYSTEM}]+history

    search=web_search(msg)

    if search:
        context.insert(1,{
            "role":"system",
            "content":"Latest web info:"+search
        })

    resp=client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=context,
        temperature=0.7
    )

    reply=resp.choices[0].message.content.strip()

    history.append({"role":"assistant","content":reply})

    img_match=re.match(r'^\[IMAGE:(.*?)\]$',reply)

    if img_match:

        q=img_match.group(1)

        img=fetch_image(q)

        return jsonify({
            "type":"image",
            "image_url":img
        })

    audio=run_tts(reply,lang)

    return jsonify({
        "reply":reply,
        "audio":audio
    })


if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
