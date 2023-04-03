from . import util

from bs4 import BeautifulSoup
from files.__main__ import app, db_session
from files.classes import Submission
from functools import lru_cache
import pytest
from time import time, sleep

class SubmissionsFixture:
	def submission_for_client(self, client, data):
		submit_get_response = client.get("/submit")
		assert submit_get_response.status_code == 200
		post_title = data.get('title', util.generate_text())
		post_body = data.get('body', util.generate_text())
		submit_post_response = client.post("/submit", data={
			"title": post_title,
			"body": post_body,
			"formkey": util.formkey_from(submit_get_response.text),
			**data,
		})
		assert submit_post_response.status_code == 200
		assert post_title in submit_post_response.text
		assert post_body in submit_post_response.text
		post_info = util.ItemData.from_html(submit_post_response.text)
		post_id_full = post_info.id_full
		assert post_id_full.startswith('post_')

		post_id = int(post_id_full[3:])

		db = db_session()
		submission = db.query(Submission).filter_by(id=post_id).first()
		assert Submission == type(submission)
		return submission

@pytest.fixture(scope="session")
def submissions():
	return SubmissionsFixture()




