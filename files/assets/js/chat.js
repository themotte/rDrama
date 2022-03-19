let socket=io()

function process_chat(json, template){
	console.log(json);
	username=json['username'];
	text=json['text'];
	ava=json['avatar']

	var my_name=$('#username').val()

	if (template=="#msg-in" || template=="#wallop" || text.includes('href="/@'+my_name+'"')){
		$(template+'-template .chat-line').addClass('chat-mention');
		notifs=notifs+1;
		if (notifs==1){
			setTimeout(flash, 500);
			ding()
		}
	}
	else {
		$(template+'-template .chat-line').removeClass('chat-mention');
	};

	should_scroll()
	$(template+'-template img').attr('src', ava)
	$(template+'-template img').attr('data-original-title', json['time'])
	$(template+'-template .userlink').attr('href', json['userlink'])
	$(template+'-template .username').text(username)
	$(template+'-template .chat-message').html(text)
	$('#chat-text').append($(template+'-template .chat-line').clone())
	scroll()
}

socket.on('speak', function(json){process_chat(json, "#chat-line")});

socket.on('connect',
	function(event) {
		console.log('connected, joining room')
		name=$('#guildname').val();

		join=($('#autojoin').val()=="True")
		if (join){
			socket.emit('join room', {'guild': name });
		}
	}
)