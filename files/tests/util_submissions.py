from . import util

from files.__main__ import app, db_session
from files.classes import Submission
from time import time, sleep


def create_submission_for_client(client, data=None):
	"""Create a submission using the provided test client."""
	if data is None:
		data = {}

	post_title = data.get('title', util.generate_text())
	post_body = data.get('body', util.generate_text())

	submit_post_response, submit_get_response = util.post_with_formkey(
		client, "/submit",
		data={
			"title": post_title,
			"body": post_body,
			**data,
		}
	)
	assert submit_post_response.status_code == 200
	assert post_title in submit_post_response.text
	assert post_body in submit_post_response.text
	post_info = util.ItemData.from_html(submit_post_response.text)
	post_id_full = post_info.id_full
	assert post_id_full.startswith('post_')

	post_id = int(post_id_full.split('_')[1])

	db = db_session()
	submission = db.query(Submission).filter_by(id=post_id).first()
	assert Submission == type(submission)
	return submission