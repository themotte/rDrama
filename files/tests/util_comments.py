from . import util

from files.__main__ import app, db_session
from files.classes import Comment
import json
import re
from time import time, sleep


def create_comment_for_client(client, post_id, data=None):
	"""Create a comment on a post using the provided test client."""
	if data is None:
		data = {}

	comment_body = data.get('body', util.generate_text())

	submit_comment_response, submit_get_response = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f'post_{post_id}',
			'parent_level': 1,
			'submission': post_id,
			"body": comment_body,
			**data,
		}
	)
	assert submit_comment_response.status_code == 200
	submit_comment_data = json.loads(submit_comment_response.text)
	assert 'comment' in submit_comment_data
	# This is terrible
	match = re.search(r'.*\bid="comment-(\d+)"', submit_comment_data['comment'])
	assert match != None
	comment_id = int(match.groups()[0])

	db = db_session()
	comment = db.query(Comment).filter_by(id=comment_id).first()
	assert Comment == type(comment)
	return comment