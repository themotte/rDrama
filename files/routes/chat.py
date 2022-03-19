import time
from files.helpers.wrappers import auth_required
from files.helpers.sanitize import sanitize
from datetime import datetime
from flask_socketio import SocketIO, emit
from files.__main__ import app
from flask import render_template
import sys

if "load_chat" in sys.argv:
	sex = SocketIO(app, async_mode='gevent-websocket')

	@app.get("/chat")
	@auth_required
	def chat( v):
		return render_template("chat.html", v=v)


	@sex.on('speak')
	@auth_required
	def speak(data, v):

		data={
			"avatar": v.profile_url,
			"username":v.username,
			"text":sanitize(data[:1000].strip()),
			"time": time.strftime("%d %b %Y at %H:%M:%S", time.gmtime(int(time.time()))),
			"userlink":v.url
		}

		emit('speak', data)
		return '', 204