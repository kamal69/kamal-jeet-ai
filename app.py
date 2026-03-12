import os
import base64
import asyncio
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv
from groq import Groq
import edge_tts

load_dotenv()

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

history = []

SYSTEM = """
You are KJ Master AI.

You understand Hindi, English, and Hinglish.
Reply in the same style as the user.

Speak naturally like ChatGPT.
"""

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KJ Master AI</title>

<style>

body{
background:#0f172a;
font-family:Arial;
color:white;
display:flex;
flex-direction:column;
height:100vh;
margin:0;
}

header{
background:#1e293b;
padding:15px;
text-align:center;
font-size:20px;
font-weight:bold;
}

#chat{
flex:1;
overflow:auto;
padding:15px;
}

.msg{
margin:10px 0;
padding:10px 14px;
border-radius:10px;
max-width:70%;
}

.user{
background:#2563eb;
margin-left:auto;
}

.ai{
background:#334155;
}

#input{
display:flex;
padding:10px;
background:#1e293b;
}

#text{
flex:1;
padding:10px;
border:none;
border-radius:10px;
outline:none;
}

button{
margin-left:6px;
padding:10px;
border:none;
border-radius:10px;
background:#6366f1;
color:white;
cursor:pointer;
}

</style>
</head>

<body>

<header>KJ Master AI</header>

<div id="chat"></div>

<div id="input">
<input id="text" placeholder="Type message">
<button onclick="send()">Send</button>
<button onclick="mic()">🎤</button>
</div>

<script>

function add(text,cls){

let div=document.createElement("div")
div.className="msg "+cls
div.innerText=text

document.getElementById("chat").appendChild(div)

document.getElementById("chat").scrollTop=999999

}

async function send(){

let input=document.getElementById("text")
let msg=input.value

if(!msg) return

add(msg,"user")

input.value=""

let res=await fetch("/chat",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({message:msg})
})

let data=await res.json()

add(data.reply,"ai")

if(data.audio){

let audio=new Audio("data:audio/mp3;base64,"+data.audio)

audio.play().catch(e=>console.log(e))

}

}

function mic(){

let SR=window.SpeechRecognition||window.webkitSpeechRecognition

if(!SR){
alert("Use Chrome browser")
return
}

let recognition=new SR()

recognition.lang="en-IN"
recognition.start()

recognition.onresult=function(e){

let text=e.results[0][0].transcript

document.getElementById("text").value=text

send()

}

}

</script>

</body>
</html>
"""

async def generate_voice(text,lang):

    voice="hi-IN-SwaraNeural" if lang=="hi" else "en-US-JennyNeural"

    communicate=edge_tts.Communicate(text,voice)

    audio=b""

    async for chunk in communicate.stream():

        if chunk["type"]=="audio":

            audio+=chunk["data"]

    return base64.b64encode(audio).decode()


def run_tts(text,lang):

    try:
        return asyncio.run(generate_voice(text,lang))
    except:
        return None


def detect_lang(text):

    hindi="अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह"

    score=sum(1 for c in text if c in hindi)

    return "hi" if score>2 else "en"


@app.route("/")
def home():

    return render_template_string(HTML)


@app.route("/chat",methods=["POST"])
def chat():

    data=request.json

    msg=data.get("message","")

    lang=detect_lang(msg)

    history.append({"role":"user","content":msg})

    resp=client.chat.completions.create(

        model="llama-3.3-70b-versatile",

        messages=[{"role":"system","content":SYSTEM}]+history,

        max_tokens=400,
        temperature=0.7
    )

    reply=resp.choices[0].message.content

    history.append({"role":"assistant","content":reply})

    if len(history)>20:
        history.pop(0)
        history.pop(0)

    audio=run_tts(reply,lang)

    return jsonify({
        "reply":reply,
        "audio":audio
    })


if __name__=="__main__":

    port=int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0",port=port)