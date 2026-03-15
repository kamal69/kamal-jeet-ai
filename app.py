import os
import base64
import urllib.request
import urllib.parse
import re
import json

from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs

load_dotenv()

app = Flask(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

history = []

# ================= SYSTEM PROMPT =================

SYSTEM = """
You are KJ Master AI - a friendly, smart AI assistant.
You understand Hindi, English and Hinglish fluently.
Always reply in the same language the user speaks.
Keep replies short and natural for voice conversation.
"""

# ================= HTML =================

HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Sarthi AI</title>
<style>

body{
background:#0d0d0d;
color:white;
font-family:Arial;
margin:0;
display:flex;
flex-direction:column;
height:100vh;
}

#chat{
flex:1;
overflow:auto;
padding:20px;
}

.msg{
margin:10px 0;
}

.user{
color:#7dd3fc;
}

.ai{
color:#fbbf24;
}

#box{
display:flex;
padding:10px;
background:#111;
}

input{
flex:1;
padding:10px;
border:none;
outline:none;
}

button{
padding:10px;
background:#c96442;
border:none;
color:white;
cursor:pointer;
}

</style>
</head>

<body>

<div id="chat"></div>

<div id="box">
<input id="text" placeholder="Ask anything...">
<button onclick="send()">Send</button>
</div>

<script>

async function send(){

const input=document.getElementById("text")

const msg=input.value

if(!msg)return

add("user",msg)

input.value=""

const res=await fetch("/chat",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({message:msg})
})

const text=await res.text()

let data

try{
data=JSON.parse(text)
}catch{
console.log(text)
add("ai","Server returned HTML error")
return
}

add("ai",data.reply)

}

function add(type,text){

const div=document.createElement("div")

div.className="msg "+type

div.innerText=text

document.getElementById("chat").appendChild(div)

}

</script>

</body>
</html>
"""

# ================= ELEVENLABS VOICE =================

def eleven_tts(text):

    try:

        audio = eleven.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            model_id="eleven_multilingual_v2",
            text=text
        )

        audio_bytes = b"".join(audio)

        return base64.b64encode(audio_bytes).decode()

    except Exception as e:

        print("ElevenLabs ERROR:", e)

        return None


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

    except Exception as e:

        print("Search error:", e)

    return None


# ================= IMAGE FETCH =================

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


# ================= ROUTES =================

@app.route("/")
def home():

    return render_template_string(HTML)


@app.route("/clear", methods=["POST"])
def clear():

    global history
    history = []

    return jsonify({"status":"cleared"})


@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json(force=True)

        msg = data.get("message","")

        history.append({
            "role":"user",
            "content":msg
        })

        messages = [
            {"role":"system","content":SYSTEM}
        ] + history

        search = web_search(msg)

        if search:
            messages.insert(1,{
                "role":"system",
                "content":"Latest web info:\n"+search
            })

        resp = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            max_tokens=300,
            temperature=0.7
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

        print("CHAT ERROR:", e)

        return jsonify({
            "reply":"Server error: "+str(e)
        })


# ================= START SERVER =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0", port=port)
