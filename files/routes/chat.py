import time
from files.helpers.wrappers import *
from files.helpers.sanitize import *
from flask import *
from files.__main__ import app, db_session
from datetime import datetime
from flask_socketio import *

sex = SocketIO(app)

@app.get("/chat")
@auth_required
def chat( v):
	return render_template("chat.html", v=v)



@sex.on('speak')
@auth_required
def speak(data, v):

	raw_text=data['text'][0:1000].lstrip().rstrip()
	if not raw_text:return

	text = sanitize(raw_text)

	data={
		"avatar": v.profile_url,
		"username":v.username,
		"text":text,
		"time": time.strftime("%d %b %Y at %H:%M:%S", time.gmtime(int(time.time()))),
		"userlink":v.url
	}

	emit('speak', data)