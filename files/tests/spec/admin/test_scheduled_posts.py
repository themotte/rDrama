'''
Scheduled posts, which admins write ahead of time for the site to post on a schedule: POST /tasks/scheduled_posts/<id>/content edits one's "title" and "body", under the same rules as submitting a post.
'''
from files.tests.spec.harness import *


def test_invalid_scheduled_post_edits_are_refused():
	admin = factories.admin(2)
	task = db.insert("tasks_repeatable", author_id=admin["id"], type_id=2, enabled=False, run_state=1, frequency_day=0, time_of_day_utc="01:00", created_utc=1000)
	db.insert("tasks_repeatable_scheduled_submissions", id=task["id"], author_id_submission=admin["id"], ghost=False, private=False, over_18=False, is_bot=False, title="t", body="text", body_html="<p>text</p>")
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/tasks/scheduled_posts/{task['id']}/content", {"title": "t", "body": ""}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()
