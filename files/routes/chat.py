import functools
import time
import uuid
from typing import Any, Final

from flask_socketio import SocketIO, emit

from files.__main__ import app, cache, limiter
from files.helpers.alerts import *
from files.helpers.config.const import *
from files.helpers.config.environment import *
from files.helpers.config.regex import *
from files.helpers.sanitize import sanitize
from files.helpers.wrappers import get_logged_in_user, is_not_permabanned, admin_level_required

def chat_is_allowed(perm_level: int=0):
	def wrapper_maker(func):
		@functools.wraps(func)
		def wrapper(*args: Any, **kwargs: Any) -> bool | None:
			v = get_logged_in_user()
			if not v or v.is_suspended_permanently or v.admin_level < perm_level:
				return abort(403)
			if v.admin_level < PERMS['CHAT_FULL_CONTROL'] and not v.chat_authorized:
				return abort(403)
			kwargs['v'] = v
			return func(*args, **kwargs)
		return wrapper
	return wrapper_maker

commands = {}

def register_command(cmd_name, permission_level = 0):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args: Any, **kwargs: Any) -> bool | None:
			v = get_logged_in_user()
			if v.admin_level < permission_level:
				send_system_reply(f"Unknown command: {cmd_name}")
				return False
			return func(*args, **kwargs)
    
		commands[cmd_name] = wrapper
		
		return wrapper
	return decorator

if app.debug:
	socketio = SocketIO(
		app,
		async_mode='gevent',
		logger=True,
		engineio_logger=True,
		debug=True,
	)
else:
	socketio = SocketIO(
		app,
		async_mode='gevent',
	)

CHAT_SCROLLBACK_ITEMS: Final[int] = 500

typing: list[str] = []
online: list[str] = []	# right now we maintain this but don't actually use it anywhere
socket_ids_to_user_ids = {}
user_ids_to_socket_ids = {}

def send_system_reply(text):
	data = {
		"id": str(uuid.uuid4()),
		"avatar": g.db.query(User).filter(User.id == NOTIFICATIONS_ID).one().profile_url,
		"user_id": NOTIFICATIONS_ID,
		"username": "System",
		"text": text,
		"text_html": sanitize(text),
		'time': int(self.created_datetimez.timestamp()),
	}
	emit('speak', data)

def get_chat_messages():
	# Query for the last visible chat messages
	result = (g.db.query(ChatMessage)
          .join(User, User.id == ChatMessage.author_id)  # Join with the User table to fetch related user data
          .order_by(ChatMessage.created_datetimez.desc())
          .limit(CHAT_SCROLLBACK_ITEMS)
          .all())
	
	# Convert the list of ChatMessage objects into a list of dictionaries
	# Also, most recent at the bottom, not the top.
	messages = [item.json_speak() for item in result[::-1]]
	
	return messages

def get_chat_userlist():
	# Query for the User.username column for users with chat_authorized == True
    result = g.db.query(User.username).filter(User.chat_authorized == True).all()
    
    # Convert the list of tuples into a flat list of usernames
    userlist = [item[0] for item in result]
    
    return userlist

@app.get("/chat")
@is_not_permabanned
@chat_is_allowed()
def chat(v):
	return render_template("chat.html", v=v)


@socketio.on('speak')
@limiter.limit("3/second;10/minute")
@chat_is_allowed()
def speak(data, v):
	limiter.check()
	if v.is_banned: return '', 403

	text = sanitize_raw(
		data['message'],
		allow_newlines=True,
		length_limit=CHAT_LENGTH_LIMIT,
	)
	if not text: return '', 400

	command = chat_command_regex.match(text)
	if command:
		command_name = command.group(1).lower()
		command_parameters = command.group(2)
		
		if command_name in commands:
			commands[command_name](command_parameters)
		else:
			send_system_reply(f"Unknown command: {command_name}")

		return

	text_html = sanitize(text)
	quotes = data['quotes']
	
	chat_message = ChatMessage()
	chat_message.author_id = v.id
	chat_message.quote_id = quotes
	chat_message.text = text
	chat_message.text_html = text_html
	g.db.add(chat_message)
	g.db.commit()

	emit('speak', chat_message.json_speak(), broadcast=True)


@socketio.on('connect')
@chat_is_allowed()
def connect(v):
	if v.username not in online:
		online.append(v.username)

	if not socket_ids_to_user_ids.get(request.sid):
		socket_ids_to_user_ids[request.sid] = v.id
		user_ids_to_socket_ids[v.id] = request.sid

	emit('online', get_chat_userlist())
	emit('catchup', get_chat_messages())
	emit('typing', typing)


@socketio.on('disconnect')
@chat_is_allowed()
def disconnect(v):
	if v.username in online:
		online.remove(v.username)

	if v.username in typing: typing.remove(v.username)

	if socket_ids_to_user_ids.get(request.sid):
		del socket_ids_to_user_ids[request.sid]
		del user_ids_to_socket_ids[v.id]

	emit('typing', typing, broadcast=True)


@socketio.on('typing')
@chat_is_allowed()
def typing_indicator(data, v):
	if data and v.username not in typing:
		typing.append(v.username)
	elif not data and v.username in typing:
		typing.remove(v.username)

	emit('typing', typing, broadcast=True)


@socketio.on('delete')
@chat_is_allowed(PERMS['CHAT_MODERATION'])
def delete(id, v):
    chat_message = g.db.query(ChatMessage).filter(ChatMessage.id == id).one_or_none()
    if chat_message:
        # Zero out all the quote_id references to this message
        messages_quoting_this = g.db.query(ChatMessage).filter(ChatMessage.quote_id == id).all()
        for message in messages_quoting_this:
            message.quote_id = None 

        # Now, delete the chat_message
        g.db.delete(chat_message)
        g.db.commit()

        emit('delete', id, broadcast=True)

@register_command('add', PERMS['CHAT_FULL_CONTROL'])
def add(user):
	print("Adding user", user)
	user_instance = g.db.query(User).filter(func.lower(User.username) == user.lower()).one_or_none()

	if user_instance:
		if user_instance.chat_authorized:
			send_system_reply(f"{user} already in this chat.")
		else:
			user_instance.chat_authorized = True
			g.db.commit()

			emit('online', get_chat_userlist(), broadcast=True)

			send_system_reply(f"Added {user} to chat.")
	else:
		send_system_reply(f"Could not find user {user}.")


@register_command('remove', PERMS['CHAT_FULL_CONTROL'])
def remove(user):
	print("Removing user", user)
	user_instance = g.db.query(User).filter(func.lower(User.username) == user.lower()).one_or_none()

	if user_instance:
		if not user_instance.chat_authorized:
			send_system_reply(f"{user} already not in this chat.")
		else:
			user_instance.chat_authorized = False
			g.db.commit()

			emit('online', get_chat_userlist(), broadcast=True)

			send_system_reply(f"Removed {user} from chat.")
	else:
		send_system_reply(f"Could not find user {user}.")
