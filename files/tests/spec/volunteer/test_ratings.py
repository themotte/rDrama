'''
Rating the comments of a volunteer duty: POST /volunteer/submit, with one form field "volunteer-assignment-<assignment id>" per rated comment, naming the assignment that gave the volunteer the comment (see test_duty), whose value is the rating: "1" high quality, "2" good, "3" neutral, "4" bad, "5" deserves a warning, "6" deserves a ban (stored as result "TopQuality", "Good", "Neutral", "Bad", "Warning", "Ban"). Only the form counts (not the query string). Each field must name one of the volunteer's open assignments: assigned to them to rate and not yet rated by them, whatever happened to it since, and no two fields the same comment. Each rating is stored as a "volunteer_janitor" row of the volunteer, the comment and the result, and the answer is a thank-you page. Fields not starting with "volunteer-" are ignored.

Each rating updates the comment's "volunteer_janitor_badness" at once, counting it. The badness comes from the first rating of each volunteer assigned the comment before they rated it (other ratings count for nothing). A rating says the comment is bad (Warning, Ban: with confidence 1; Bad: 0.5) or not (TopQuality, Good: 1; Neutral: 0.5), and counts with the confidence times the volunteer's weight, which comes from their past accuracy c ("volunteer_janitor_correctness"): 0 up to c = 0.5, rising evenly to 1 at c = 1. With W the total counted weight and B the part of it saying bad, the badness is 0.5 when W is 0; otherwise, with p = (B + 0.5) / (W + 1), it is max(B / (W + 1 - p), 0.5) when p > 0.5, and min((B + p) / (W + p), 0.5) when not.

Ratings by shadowbanned volunteers are stored but count for nothing: shadowbanning a volunteer takes their ratings out of the badness of the comments they rated, and lifting the shadowban puts them back.

Refused, storing nothing of the request: anonymous users (sent to log in); suspended users, permanently or not, and API clients (403); with 400, a "volunteer-" field of another kind, an assignment id that isn't a whole number in digits, a value other than those six, a field given twice, or a field that doesn't name one of the volunteer's open assignments.
'''
import time

import pytest

from files.tests.spec.harness import *

RESULTS = {"1": "TopQuality", "2": "Good", "3": "Neutral", "4": "Bad", "5": "Warning", "6": "Ban"}


def _assigned_comment(volunteer):
	comment = factories.comment(factories.user(), factories.post(factories.user()), state_report="REPORTED")
	factories.report(factories.user(), comment)
	factories.assignment(volunteer, comment)
	return comment


def _field(volunteer, comment):
	'''The form field rating `comment` for `volunteer`, named by the assignment that gave it to them.'''
	return f"volunteer-assignment-{db.row('volunteer_janitor', user_id=volunteer['id'], comment_id=comment['id'], result='Pending')['id']}"


def _rating(volunteer, comment, result):
	return {"user_id": volunteer["id"], "comment_id": comment["id"], "result": result}


@pytest.mark.parametrize("value", RESULTS)
def test_a_rating_is_stored(value):
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, comment): value})

	assert_html(r, 200)
	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, RESULTS[value])]})


def test_a_duty_is_rated_in_one_request():
	volunteer = factories.user()
	comments = [_assigned_comment(volunteer) for _ in range(3)]
	client = as_user(volunteer)

	with db_diff() as d:
		client.post("/volunteer/submit", {_field(volunteer, c): str(n) for n, c in enumerate(comments, 1)})

	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, c, RESULTS[str(n)]) for n, c in enumerate(comments, 1)]})


def test_other_fields_are_ignored():
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, comment): "2", "comment": "fine", "janitor-1": "6"})

	assert_html(r, 200)
	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, "Good")]})


def test_an_empty_submission_changes_nothing():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post("/volunteer/submit", {})

	assert_html(r, 200)
	d.assert_exactly()


@pytest.mark.parametrize("kind", ["gardener", "janitor"])
def test_other_kinds_of_volunteer_fields_are_refused(kind):
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {f"volunteer-{kind}-{comment['id']}": "1"})

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
		client.post("/volunteer/submit", {_field(volunteer, comment): "4"})

	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, "Bad")]})


def _no_assignment(volunteer):
	unused = db.execute("SELECT nextval('volunteer_janitor_id_seq')")
	return {f"volunteer-assignment-{unused}": "6"}


def _rated(volunteer):
	comment = _assigned_comment(volunteer)
	db.insert("volunteer_janitor", user_id=volunteer["id"], comment_id=comment["id"], result="Good")
	return {_field(volunteer, comment): "6"}


def _others_assignment(volunteer):
	other = factories.user()
	return {_field(other, _assigned_comment(other)): "6"}


def _own_rating(volunteer):
	comment = _assigned_comment(volunteer)
	rating = db.insert("volunteer_janitor", user_id=volunteer["id"], comment_id=comment["id"], result="Good")
	return {f"volunteer-assignment-{rating['id']}": "6"}


def _one_comment_twice(volunteer):
	comment = _assigned_comment(volunteer)
	first = _field(volunteer, comment)
	again = factories.assignment(volunteer, comment)
	return {first: "6", f"volunteer-assignment-{again['id']}": "6"}


def _one_assignment_spelled_twice(volunteer):
	field = _field(volunteer, _assigned_comment(volunteer))
	number = field.removeprefix("volunteer-assignment-")
	return {field: "6", f"volunteer-assignment-0{number}": "1"}


def _value(value):
	return lambda volunteer: {_field(volunteer, _assigned_comment(volunteer)): value}


def _id(comment_id):
	def fields(volunteer):
		_assigned_comment(volunteer)
		return {f"volunteer-assignment-{comment_id}": "6"}
	return fields


def _one_bad_among_good(volunteer):
	good = _assigned_comment(volunteer)
	return {_field(volunteer, good): "2", **_no_assignment(volunteer)}


REFUSED = {
	"no assignment": _no_assignment,
	"own rating": _own_rating,
	"one comment twice": _one_comment_twice,
	"one assignment spelled twice": _one_assignment_spelled_twice,
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
		r = client.post("/volunteer/submit", {_field(volunteer, comment): ["6", "1"]})

	assert_status(r, 400)
	d.assert_exactly()


def test_ratings_in_the_query_string_are_ignored():
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post(f"/volunteer/submit?{_field(volunteer, comment)}=6", {})

	assert_html(r, 200)
	d.assert_exactly()


# Badness

@pytest.mark.parametrize("value, badness", [("1", 0.2), ("2", 0.2), ("3", 0.4), ("4", 0.6), ("5", 0.8), ("6", 0.8)], ids=RESULTS.values())
def test_a_fully_weighted_rating_sets_the_badness(value, badness):
	volunteer = factories.user(volunteer_janitor_correctness=1.0)
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		client.post("/volunteer/submit", {_field(volunteer, comment): value})

	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, RESULTS[value])]}, updated={"comments": {comment["id"]: {"volunteer_janitor_badness": pytest.approx(badness)}}})


@pytest.mark.parametrize("correctness, badness", [(0.5, 0.5), (0.75, 0.6), (0.3, 0.5)])
def test_a_rating_weighs_by_the_volunteers_accuracy(correctness, badness):
	volunteer = factories.user(volunteer_janitor_correctness=correctness)
	comment = _assigned_comment(volunteer)

	as_user(volunteer).post("/volunteer/submit", {_field(volunteer, comment): "6"})

	assert db.row("comments", id=comment["id"])["volunteer_janitor_badness"] == pytest.approx(badness)


@pytest.mark.parametrize("earlier, badness", [("Ban", 0.5), ("Warning", 0.5), ("Good", 1 / 13), ("Ban-unassigned", 0.2), ("Ban-then-Good", 0.5)])
def test_the_badness_counts_each_assigned_volunteers_rating(earlier, badness):
	'''The volunteer rates Good; another fully weighted volunteer rated before them (once, or twice as older versions allowed: their first rating counts).'''
	other, volunteer = factories.user(volunteer_janitor_correctness=1.0), factories.user(volunteer_janitor_correctness=1.0)
	comment = _assigned_comment(volunteer)
	if earlier != "Ban-unassigned":
		factories.assignment(other, comment)
	first, _, second = earlier.removesuffix("-unassigned").partition("-then-")
	db.insert("volunteer_janitor", user_id=other["id"], comment_id=comment["id"], result=first)
	if second:
		db.insert("volunteer_janitor", user_id=other["id"], comment_id=comment["id"], result=second)

	as_user(volunteer).post("/volunteer/submit", {_field(volunteer, comment): "2"})

	assert db.row("comments", id=comment["id"])["volunteer_janitor_badness"] == pytest.approx(badness)


def test_two_bans_make_a_comment_worse_than_one():
	other, volunteer = factories.user(volunteer_janitor_correctness=1.0), factories.user(volunteer_janitor_correctness=1.0)
	comment = _assigned_comment(volunteer)
	factories.assignment(other, comment)
	db.insert("volunteer_janitor", user_id=other["id"], comment_id=comment["id"], result="Ban")

	as_user(volunteer).post("/volunteer/submit", {_field(volunteer, comment): "6"})

	assert db.row("comments", id=comment["id"])["volunteer_janitor_badness"] == pytest.approx(2 / (2 + 1 / 6))


# Volunteers' standing

@pytest.mark.parametrize("permanently", [True, False], ids=["permanently", "temporarily"])
def test_suspended_volunteers_cant_rate(permanently):
	volunteer = factories.user(is_banned=factories.admin(2)["id"], unban_utc=0 if permanently else int(time.time()) + 86400, volunteer_janitor_correctness=1.0)
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, comment): "6"})

	assert_status(r, 403)
	d.assert_exactly()


def test_a_shadowbanned_volunteers_rating_is_stored_but_doesnt_count():
	volunteer = factories.user(shadowbanned="somemod", volunteer_janitor_correctness=1.0)
	comment = _assigned_comment(volunteer)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, comment): "6"})

	assert_html(r, 200)
	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, "Ban")]})


def test_a_shadowbanned_volunteers_earlier_rating_doesnt_count_either():
	shadowbanned, volunteer = factories.user(shadowbanned="somemod", volunteer_janitor_correctness=1.0), factories.user(volunteer_janitor_correctness=1.0)
	comment = _assigned_comment(volunteer)
	factories.assignment(shadowbanned, comment)
	db.insert("volunteer_janitor", user_id=shadowbanned["id"], comment_id=comment["id"], result="Ban")

	as_user(volunteer).post("/volunteer/submit", {_field(volunteer, comment): "2"})

	assert db.row("comments", id=comment["id"])["volunteer_janitor_badness"] == pytest.approx(0.2)


def _rated_by(volunteer):
	'''Two comments `volunteer` (fully weighted) rated Ban, the second also rated Good by another fully weighted volunteer, with the badness those ratings left.'''
	other = factories.user(volunteer_janitor_correctness=1.0)
	alone, shared = _assigned_comment(volunteer), _assigned_comment(volunteer)
	factories.assignment(other, shared)
	as_user(volunteer).post("/volunteer/submit", {_field(volunteer, alone): "6", _field(volunteer, shared): "6"})
	as_user(other).post("/volunteer/submit", {_field(other, shared): "2"})
	return alone, shared


def test_shadowbanning_a_volunteer_takes_their_ratings_out():
	volunteer = factories.user(volunteer_janitor_correctness=1.0)
	alone, shared = _rated_by(volunteer)
	client = as_user(factories.admin(2))

	with db_diff() as d:
		client.post(f"/shadowban/{volunteer['id']}", headers=XHR)

	assert d.updated["comments"][(alone["id"],)] == {"volunteer_janitor_badness": pytest.approx(0.5)}
	assert d.updated["comments"][(shared["id"],)] == {"volunteer_janitor_badness": pytest.approx(0.2)}


def test_lifting_a_volunteers_shadowban_puts_their_ratings_back():
	volunteer = factories.user(volunteer_janitor_correctness=1.0)
	alone, shared = _rated_by(volunteer)
	db.update("users", {"id": volunteer["id"]}, shadowbanned="somemod")
	db.update("comments", {"id": alone["id"]}, volunteer_janitor_badness=0.5)
	db.update("comments", {"id": shared["id"]}, volunteer_janitor_badness=0.2)
	client = as_user(factories.admin(2))

	with db_diff() as d:
		client.post(f"/unshadowban/{volunteer['id']}", headers=XHR)

	assert d.updated["comments"][(alone["id"],)] == {"volunteer_janitor_badness": pytest.approx(0.8)}
	assert d.updated["comments"][(shared["id"],)] == {"volunteer_janitor_badness": pytest.approx(0.5)}


def test_api_clients_are_refused():
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	client = as_api(factories.api_token(volunteer))

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, comment): "6"})

	assert_status(r, 403)
	d.assert_exactly()
