import os
import base64
import json
import re
import urllib.request
import urllib.parse

from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs

load_dotenv()

app = Flask(__name__)

# API KEYS
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
eleven = ElevenLabs(api_key=ELEVEN_API_KEY)

history = []

SYSTEM = """
You are KJ Master AI.
Speak Hindi, English, Hinglish.
Keep replies short.
"""

# ================= SIMPLE UI =================

HTML = """
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
display:flex;
flex-direction:column;
height:100vh;
margin:0;
}

#chat{
flex:1;
overflow:auto;
padding:20px;
}

.msg{
margin:10px 0;
}

.user{color:#7dd3fc}
.ai{color:#fbbf24}

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
<input id="text" placeholder="Ask something...">
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

# ================= HOME =================

@app.route("/")
def home():
    return render_template_string(HTML)

# ================= HEALTH =================

@app.route("/health")
def health():
    return "OK"

# ================= CHAT =================

@app.route("/chat", methods=["POST"])
def chat():

    try:

        data=request.get_json(force=True)

        msg=data.get("message","")

        history.append({"role":"user","content":msg})

        messages=[{"role":"system","content":SYSTEM}]+history

        resp=client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages
        )

        reply=resp.choices[0].message.content

        history.append({"role":"assistant","content":reply})

        return jsonify({"reply":reply})

    except Exception as e:

        print("ERROR:",e)

        return jsonify({
            "reply":"Server error: "+str(e)
        })

# ================= START =================

if __name__=="__main__":

    port=int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0",port=port)
