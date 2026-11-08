'''
Rating the comments of a volunteer duty: POST /volunteer/submit, with one form field "volunteer-janitor-<comment id>" per rated comment whose value is the rating: "1" high quality, "2" good, "3" neutral, "4" bad, "5" deserves a warning, "6" deserves a ban (stored as result "TopQuality", "Good", "Neutral", "Bad", "Warning", "Ban"). Each rating is stored as a "volunteer_janitor" row of the volunteer, the comment and the result, and the answer is a thank-you page. Fields not starting with "volunteer-" are ignored.

Ratings change a comment's volunteer badness only by the weight of the volunteers giving them, which comes from their past accuracy: a volunteer whose "volunteer_janitor_correctness" is 0.5 or less weighs nothing.

Refused: anonymous users (sent to log in); a "volunteer-" field of another kind (400).
'''
import pytest

from files.tests.spec.harness import *

RESULTS = {"1": "TopQuality", "2": "Good", "3": "Neutral", "4": "Bad", "5": "Warning", "6": "Ban"}


def _assigned_comment(volunteer):
	comment = factories.comment(factories.user(), factories.post(factories.user()), state_report="REPORTED")
	factories.report(factories.user(), comment)
	factories.assignment(volunteer, comment)
	return comment


def _rating(volunteer, comment, result):
	return {"user_id": volunteer["id"], "comment_id": comment["id"], "result": result}


@pytest.mark.parametrize("value", RESULTS)
def test_a_rating_is_stored(value):
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {f"volunteer-janitor-{comment['id']}": value})

	assert_html(r, 200)
	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, RESULTS[value])]})


def test_a_duty_is_rated_in_one_request():
	volunteer = factories.user()
	comments = [_assigned_comment(volunteer) for _ in range(3)]
	client = as_user(volunteer)

	with db_diff() as d:
		client.post("/volunteer/submit", {f"volunteer-janitor-{c['id']}": str(n) for n, c in enumerate(comments, 1)})

	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, c, RESULTS[str(n)]) for n, c in enumerate(comments, 1)]})


def test_other_fields_are_ignored():
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {f"volunteer-janitor-{comment['id']}": "2", "comment": "fine", "janitor-1": "6"})

	assert_html(r, 200)
	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, "Good")]})


def test_an_empty_submission_changes_nothing():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post("/volunteer/submit", {})

	assert_html(r, 200)
	d.assert_exactly()


def test_other_kinds_of_volunteer_fields_are_refused():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post("/volunteer/submit", {"volunteer-gardener-1": "1"})

	assert_status(r, 400)
	d.assert_exactly()


def test_visitors_are_sent_to_log_in():
	with db_diff() as d:
		r = anon().post("/volunteer/submit", {})

	assert_login_redirect(r, "/volunteer/submit")
	d.assert_exactly()
