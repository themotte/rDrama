from flask import *
import time
from .security import *


def session_over18(board):

	now = int(time.time())

	return session.get('over_18', {}).get(board.base36id, 0) >= now


def session_isnsfl(board):

	now = int(time.time())

	return session.get('show_nsfl', {}).get(board.base36id, 0) >= now


def make_logged_out_formkey(t):

	s = f"{t}+{session['session_id']}"

	return generate_hash(s)


def validate_logged_out_formkey(t, k):

	now = int(time.time())
	if now - t > 3600:
		return False

	s = f"{t}+{session['session_id']}"

	return validate_hash(s, k)
