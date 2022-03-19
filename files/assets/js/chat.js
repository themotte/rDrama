let socket=io()

document.getElementById('chatsend').onclick = function () {
    console.log('clicked')
    text = document.getElementById('input-text').value
    socket.emit('speak', text);
    document.getElementById('input-text').value = ''
}

socket.on('speak', function() {
	console.log(json);
	document.getElementById('img').src = json['avatar']
	document.getElementsByClassName('userlink')[0].href = json['userlink']
	document.getElementsByClassName('username')[0].value = json['username']
	document.getElementsByClassName('chat-message').innerHTML = json['text']
	document.getElementById('chat-text').append(document.getElementById('chat-line-template .chat-line').cloneNode())
})