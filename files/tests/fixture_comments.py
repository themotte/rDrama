from . import util

from bs4 import BeautifulSoup
from files.__main__ import app, db_session
from files.classes import Comment
from functools import lru_cache
import json
import re
import pytest
from time import time, sleep

class CommentsFixture:
	def comment_for_client(self, client, post_id, data):
		submit_get_response = client.get("/submit")
		assert submit_get_response.status_code == 200
		comment_body = data.get('body', util.generate_text())
		submit_comment_response = client.post("/comment", data={
			"parent_fullname": f't2_{post_id}',
			'parent_level': 1,
			'submission': post_id,
			"body": comment_body,
			"formkey": util.formkey_from(submit_get_response.text),
			**data,
		})
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

@pytest.fixture(scope="session")
def comments():
	return CommentsFixture()
