'''
Rating the comments of a volunteer duty: POST /volunteer/submit, with one form field "volunteer-janitor-<comment id>" per rated comment whose value is the rating: "1" high quality, "2" good, "3" neutral, "4" bad, "5" deserves a warning, "6" deserves a ban (stored as result "TopQuality", "Good", "Neutral", "Bad", "Warning", "Ban"). Only the form counts (not the query string). Each rated comment must be one of the volunteer's open assignments: assigned to them to rate (see test_duty) and not yet rated by them, whatever happened to it since. Each rating is stored as a "volunteer_janitor" row of the volunteer, the comment and the result, and the answer is a thank-you page. Fields not starting with "volunteer-" are ignored.

Ratings change a comment's volunteer badness only by the weight of the volunteers giving them, which comes from their past accuracy: a volunteer whose "volunteer_janitor_correctness" is 0.5 or less weighs nothing.

Refused, storing nothing of the request: anonymous users (sent to log in); with 400, a "volunteer-" field of another kind, a comment id that isn't a whole number in digits, a value other than those six, a field given twice, or a comment that isn't one of the volunteer's open assignments.
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


def test_an_open_assignment_is_rated_whatever_happened_since():
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	db.update("comments", {"id": comment["id"]}, state_report="RESOLVED", state_mod="REMOVED")
	client = as_user(volunteer)

	with db_diff() as d:
		client.post("/volunteer/submit", {f"volunteer-janitor-{comment['id']}": "4"})

	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, "Bad")]})


def _unassigned(volunteer):
	comment = factories.comment(factories.user(), factories.post(factories.user()), state_report="REPORTED")
	factories.report(factories.user(), comment)
	return {f"volunteer-janitor-{comment['id']}": "6"}


def _rated(volunteer):
	comment = _assigned_comment(volunteer)
	db.insert("volunteer_janitor", user_id=volunteer["id"], comment_id=comment["id"], result="Good")
	return {f"volunteer-janitor-{comment['id']}": "6"}


def _others_assignment(volunteer):
	comment = _assigned_comment(factories.user())
	return {f"volunteer-janitor-{comment['id']}": "6"}


def _value(value):
	return lambda volunteer: {f"volunteer-janitor-{_assigned_comment(volunteer)['id']}": value}


def _id(comment_id):
	def fields(volunteer):
		_assigned_comment(volunteer)
		return {f"volunteer-janitor-{comment_id}": "6"}
	return fields


def _one_bad_among_good(volunteer):
	good = _assigned_comment(volunteer)
	return {f"volunteer-janitor-{good['id']}": "2", **_unassigned(volunteer)}


REFUSED = {
	"unassigned": _unassigned,
	"already rated": _rated,
	"someone else's assignment": _others_assignment,
	"pending as a value": _value("0"),
	"value too big": _value("7"),
	"value not a number": _value("bad"),
	"value padded": _value(" 6"),
	"value signed": _value("+6"),
	"value with a leading zero": _value("06"),
	"id not a number": _id("abc"),
	"id with an underscore": _id("1_0"),
	"id too large": _id(str(2**31)),
	"one bad among good": _one_bad_among_good,
}


@pytest.mark.parametrize("case", REFUSED)
def test_bad_ratings_are_refused(case):
	volunteer = factories.user()
	fields = REFUSED[case](volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", fields)

	assert_status(r, 400)
	d.assert_exactly()


def test_a_field_given_twice_is_refused():
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {f"volunteer-janitor-{comment['id']}": ["6", "1"]})

	assert_status(r, 400)
	d.assert_exactly()


def test_ratings_in_the_query_string_are_ignored():
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post(f"/volunteer/submit?volunteer-janitor-{comment['id']}=6", {})

	assert_html(r, 200)
	d.assert_exactly()
