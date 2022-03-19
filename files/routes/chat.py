import time
from os import remove
from PIL import Image as IMAGE

from files.helpers.wrappers import *
from files.helpers.alerts import *
from files.helpers.sanitize import *
from files.helpers.security import *
from files.helpers.get import *
from files.helpers.images import *
from files.helpers.const import *
from files.classes import *
from flask import *
from files.__main__ import app, cache, limiter, db_session
from .front import frontlist
from files.helpers.discord import add_role
from datetime import datetime
import requests
from urllib.parse import quote, urlencode



import sys
from flask_socketio import *

month = datetime.now().strftime('%B')

sex = SocketIO(
	app
	)

@app.get("/chat")
@auth_required
def chat( v):
	return render_template("chat.html", v=v)


SIDS={}

COMMANDS={}
HELP={}

TYPING={}



@sex.on('connect')
def socket_connect_auth_user():


	g.db=db_session()

	v=get_logged_in_user()

	if v.id in SIDS:
		SIDS[v.id].append(request.sid)
	else:
		SIDS[v.id]=[request.sid]


	emit("status", {'status':"connected"})

	g.db.close()


def socket_auth_required(f):

	def wrapper(*args, **kwargs):

		g.db=db_session()
		v=get_logged_in_user()

		if request.sid not in SIDS.get(v.id, []):
			if v.id in SIDS:
				SIDS[v.id].append(request.sid)
			else:
				SIDS[v.id]=[request.sid]

		f(*args, v, **kwargs)
		g.db.close()


	wrapper.__name__=f.__name__
	return wrapper



@sex.on('join room')
@socket_auth_required
def join_guild_room(data, v):

	return True




@sex.on('leave room')
@socket_auth_required
def leave_guild_room(data, v):
	emit("status", {'status':f"Left #{guild.name}"})




@sex.on('speak')
@socket_auth_required
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