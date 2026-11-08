'''
Rating the comments of a volunteer duty: POST /volunteer/submit, with one form field "volunteer-assignment-<assignment id>" per rated comment, naming the assignment that gave the volunteer the comment (see test_duty), whose value is the rating: "1" high quality, "2" good, "3" neutral, "4" bad, "5" deserves a warning, "6" deserves a ban (stored as result "TopQuality", "Good", "Neutral", "Bad", "Warning", "Ban"). Only the form counts (not the query string). Each field must name one of the volunteer's assignments: assigned to them to rate and not yet rated by them, and no two fields the same comment. An assignment's rating is taken only within an hour of the assignment (a duty is rated in one sitting), and only while the comment is still one duties are made of, whoever the volunteer (see test_duty): its reports open, visible, not deleted, not distinguished, pinned or marked as a ban's reason, with no distinguished direct reply, and by an author who isn't shadowbanned. Ratings of assignments that ran out, or whose comment stopped being so (it may become so again), aren't stored, while the request's other ratings are, and the answer is the same thank-you page either way. Each rating is stored as a "volunteer_janitor" row of the volunteer, the comment and the result, and the answer is a thank-you page. Fields not starting with "volunteer-" are ignored.

Each rating updates the comment's "volunteer_janitor_badness" at once, counting it. The badness comes from the first rating of each volunteer assigned the comment before they rated it, in the order they were stored (of two stored at the same moment, the one with the lower id first); other ratings count for nothing. A rating says the comment is bad (Warning, Ban: with confidence 1; Bad: 0.5) or not (TopQuality, Good: 1; Neutral: 0.5), and counts with the confidence times the volunteer's weight, which comes from their past accuracy c ("volunteer_janitor_correctness"): 0 up to c = 0.5, rising evenly to 1 at c = 1. With W the total counted weight and B the part of it saying bad, the badness is 0.5 when W is 0; otherwise, with p = (B + 0.5) / (W + 1), it is max(B / (W + 1 - p), 0.5) when p > 0.5, and min((B + p) / (W + p), 0.5) when not.

Ratings by shadowbanned volunteers are stored but count for nothing: shadowbanning a volunteer takes their ratings out of the badness of the comments they rated, and lifting the shadowban puts them back.

Refused, storing nothing of the request: anonymous users (sent to log in); suspended users, permanently or not, and API clients (403); with 400, a "volunteer-" field of another kind, an assignment id that isn't a whole number in digits, a value other than those six, a field given twice, or a field that doesn't name one of the volunteer's unrated assignments.
'''
import time
from datetime import datetime, timezone

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


def _distinguished_reply(comment):
	factories.comment(factories.admin(2), db.row("submissions", id=comment["parent_submission"]), comment, distinguish_level=1)


def _shadowbanned_author(comment):
	db.update("users", {"id": comment["author_id"]}, shadowbanned="somemod")


NO_LONGER_WANTED = {
	"reports resolved": lambda c: db.update("comments", {"id": c["id"]}, state_report="RESOLVED"),
	"reports ignored": lambda c: db.update("comments", {"id": c["id"]}, state_report="IGNORED"),
	"removed": lambda c: db.update("comments", {"id": c["id"]}, state_mod="REMOVED"),
	"held": lambda c: db.update("comments", {"id": c["id"]}, state_mod="FILTERED"),
	"deleted": lambda c: db.update("comments", {"id": c["id"]}, state_user_deleted_utc="2020-01-01T00:00:00Z"),
	"distinguished": lambda c: db.update("comments", {"id": c["id"]}, distinguish_level=1),
	"pinned": lambda c: db.update("comments", {"id": c["id"]}, is_pinned="somemod"),
	"banned for": lambda c: db.update("comments", {"id": c["id"]}, bannedfor=True),
	"distinguished reply": _distinguished_reply,
	"shadowbanned author": _shadowbanned_author,
}


@pytest.mark.parametrize("change", NO_LONGER_WANTED)
def test_ratings_of_comments_no_longer_wanted_arent_stored(change):
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	NO_LONGER_WANTED[change](comment)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, comment): "4"})

	assert_html(r, 200)
	d.assert_exactly()


@pytest.mark.parametrize("hours, stored", [(0.9, True), (1.1, False)])
def test_an_assignment_runs_out_after_an_hour(hours, stored):
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	db.execute("UPDATE volunteer_janitor SET recorded_datetimez = now() - :hours * interval '1 hour' WHERE user_id = :id", hours=hours, id=volunteer["id"])
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, comment): "4"})

	assert_html(r, 200)
	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, "Bad")]} if stored else None)


def test_the_other_ratings_of_the_request_are_stored():
	volunteer = factories.user()
	wanted, unwanted = _assigned_comment(volunteer), _assigned_comment(volunteer)
	NO_LONGER_WANTED["reports resolved"](unwanted)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, wanted): "2", _field(volunteer, unwanted): "6"})

	assert_html(r, 200)
	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, wanted, "Good")]})


def test_a_comment_wanted_again_takes_ratings_again():
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	db.update("comments", {"id": comment["id"]}, is_pinned="somemod")
	db.update("comments", {"id": comment["id"]}, is_pinned=None)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, comment): "3"})

	assert_html(r, 200)
	d.assert_exactly(inserted={"volunteer_janitor": [_rating(volunteer, comment, "Neutral")]})


@pytest.mark.parametrize("bad", ["value", "already rated"])
def test_bad_ratings_of_comments_no_longer_wanted_are_still_refused(bad):
	volunteer = factories.user()
	comment = _assigned_comment(volunteer)
	if bad == "already rated":
		db.insert("volunteer_janitor", user_id=volunteer["id"], comment_id=comment["id"], result="Good")
	NO_LONGER_WANTED["reports resolved"](comment)
	client = as_user(volunteer)

	with db_diff() as d:
		r = client.post("/volunteer/submit", {_field(volunteer, comment): "9" if bad == "value" else "4"})

	assert_status(r, 400)
	d.assert_exactly()


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


@pytest.mark.parametrize("first, badness", [("Ban", 0.5), ("Good", 1 / 13)])
def test_of_two_ratings_stored_at_once_the_first_stored_counts(first, badness):
	'''As test_the_badness_counts_each_assigned_volunteers_rating, the other volunteer's two ratings stored at the same moment.'''
	other, volunteer = factories.user(volunteer_janitor_correctness=1.0), factories.user(volunteer_janitor_correctness=1.0)
	comment = _assigned_comment(volunteer)
	factories.assignment(other, comment, at=datetime(2024, 1, 1, tzinfo=timezone.utc))
	for result in (first, "Good" if first == "Ban" else "Ban"):
		factories.rating(other, comment, result, at=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc))

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
