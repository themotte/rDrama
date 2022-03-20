let socket=io()

document.getElementById('chatsend').onclick = function () {
    console.log('clicked')
    text = document.getElementById('input-text').value
    socket.emit('speak', text);
    document.getElementById('input-text').value = ''
}

socket.on('speak', function(json) {
	console.log(json);
	document.getElementsByClassName('desktop-avatar')[0].src = json['avatar']
	document.getElementsByClassName('userlink')[0].href = json['userlink']
	document.getElementsByClassName('username')[0].innerHTML = json['username']
	document.getElementsByClassName('chat-message')[0].innerHTML = json['text']
	document.getElementById('chat-text').append(document.getElementsByClassName('chat-line')[0].cloneNode(true))
})