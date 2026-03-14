function send(){

let text = document.getElementById("msg").value

fetch("/chat",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({message:text})
})
.then(res=>res.json())
.then(data=>{

document.getElementById("chat").innerHTML += "<p>"+data.reply+"</p>"

if(data.audio){

let audio = new Audio("data:audio/mp3;base64,"+data.audio)

audio.play()

}

})

}
