let socket=io()

document.getElementById('chatsend').onclick = function () {
    console.log('clicked')
    text = document.getElementById('input-text').val()
    socket.emit('speak', text);
    document.getElementById('input-text').val('')
}

socket.on('speak', function() {
	console.log(json);
	username=json['username'];
	text=json['text'];
	ava=json['avatar']

	document.getElementById('chat-line-template img').attr('src', ava)
	document.getElementById('chat-line-template img').attr('data-original-title', json['time'])
	document.getElementById('chat-line-template .userlink').attr('href', json['userlink'])
	document.getElementById('chat-line-template .username').text(username)
	document.getElementById('chat-line-template .chat-message').html(text)
	document.getElementById('chat-text').append(document.getElementById('chat-line-template .chat-line').clone())
})