'''
The nightly volunteer recalc: the "volunteer_janitor_recalc" built-in job (spec/scheduler/test_builtin_jobs.py), which the `volunteer_janitor_recalc` command also runs. It works out each volunteer's accuracy (`users.volunteer_janitor_correctness`, which weighs their ratings in a comment's badness: see test_ratings.py) afresh from all their ratings.

The ratings it learns from are the ones a comment's badness counts (test_ratings.py): each volunteer's first rating of each comment after they were first assigned it, in the order they were stored (of two stored at the same moment, the one with the lower id first). Comments their author has deleted are left out. Assignments never rated count for nothing.

The moderators' verdict on a comment comes from negative notes about its author: notes tagged Warning, Tempban, Permban, Spam or Bot, whatever post or comment they name, taken at their time rounded down to the second. The comment is
- bad when any of its distinguished direct replies was posted less than 15 minutes (900 s) from such a note, before or after;
- otherwise ignored, when such a note came strictly after the comment and less than 48 hours after it;
- otherwise not bad.

Each rating says bad (Warning, Ban: confidence 1; Bad: 0.5) or not (TopQuality, Good: 1; Neutral: 0.5). An accuracy a gives a weight w(a): 0 up to a = 0.5, rising evenly to 1 at a = 1. Every volunteer starts at accuracy 0.2, whatever is stored, and 100 rounds follow. Each round first estimates every comment from the previous round's accuracies, then updates every accuracy from those estimates:
- A comment's estimate is (B + 0.5) / (W + 1), where W sums the weights counting on it and B the part of them saying bad. A verdict of bad adds 4 to both, not bad adds 4 to W, ignored adds nothing. Each counted rating adds its confidence times the volunteer's weight: 4 for admins (account admin level 1 or more), w(their accuracy) for anyone else. Ratings by shadowbanned volunteers, admins included, add nothing, though their own accuracy is worked out from them like anyone's. A volunteer's own ratings are part of the estimates they are scored against.
- A volunteer's score is V / N, starting from N = 2 and V = 0.4, over their ratings of comments that aren't ignored: each adds k = confidence × s to N, and to V too when it was right (it says bad exactly when the estimate is above 0.5), where s = clamp((|estimate − 0.5| − 0.1) / 0.4, 0, 1). Their accuracy then moves a fifth of the way to their score: a ← 0.8 a + 0.2 × score.

Every volunteer who stored a rating gets the result, so one none of whose ratings it learns from ends at 0.2; volunteers who never rated keep what is stored.
'''
import calendar
from datetime import datetime, timedelta, timezone

import pytest

from files.tests.spec.harness import *

T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
'''When the comments rated here are posted.'''
REPLY = T0 + timedelta(days=3)
'''When the moderators reply: past the 48 hours, so the reply alone decides.'''
NEGATIVE = ["Warning", "Tempban", "Permban", "Spam", "Bot"]
SAYS = {"TopQuality": (False, 1), "Good": (False, 1), "Neutral": (False, 0.5), "Bad": (True, 0.5), "Warning": (True, 1), "Ban": (True, 1)}
'''Each rating: whether it says bad, and its confidence.'''
EVERY_DAY = 0b11111110


def _epoch(at: datetime) -> int:
	return calendar.timegm(at.utctimetuple())


def _after_100_rounds(score: float) -> float:
	'''The accuracy 100 rounds reach from 0.2 toward a score that stays the same throughout.'''
	return score + (0.2 - score) * 0.8 ** 100


def _lone(judged_bad: bool, result: str) -> float:
	'''A lone non-admin volunteer's accuracy from one rating of a comment the moderators judged: their weight stays 0, so the estimate stays 0.9 (bad) or 0.1 (not bad), and s = 0.75.'''
	says_bad, confidence = SAYS[result]
	k = confidence * 0.75
	return _after_100_rounds((0.4 + k * (says_bad == judged_bad)) / (2 + k))


RIGHT, WRONG, UNTRAINED = _lone(True, "Ban"), _lone(True, "Good"), 0.2


def _author(comment) -> dict:
	return {"id": comment["author_id"]}


def _comment(author=None, at=T0, **overrides) -> dict:
	return factories.comment(author or factories.user(), factories.post(factories.user()), created_utc=_epoch(at), **overrides)


def _reply(comment, at=REPLY, **overrides) -> dict:
	'''A moderator's distinguished reply to `comment`.'''
	post = db.row("submissions", id=comment["parent_submission"])
	return factories.comment(factories.admin(2), post, parent=comment, created_utc=_epoch(at), **{"distinguish_level": 1, **overrides})


def _bad(**overrides) -> dict:
	'''A comment the moderators judged bad: a distinguished reply and a warning at the same moment.'''
	comment = _comment(**overrides)
	_reply(comment)
	factories.note(_author(comment), "Warning", REPLY)
	return comment


def _ignored() -> dict:
	comment = _comment()
	factories.note(_author(comment), "Warning", T0 + timedelta(hours=1))
	return comment


def _judged(judged_bad: bool) -> dict:
	return _bad() if judged_bad else _comment()


def _rate(volunteer, comment, result):
	factories.assignment(volunteer, comment)
	factories.rating(volunteer, comment, result)


def _recalc(via="command"):
	if via == "command":
		r = cli("volunteer_janitor_recalc")
		assert_cli_ok(r)
		assert r.output.strip()
		return
	job = factories.job(factories.admin(2), "files.commands.volunteer_janitor_recalc", "volunteer_janitor_recalc_cron", frequency_day=EVERY_DAY)
	run_scheduler(datetime.now(timezone.utc) + timedelta(days=1))
	assert [r["traceback_str"] for r in db.rows("tasks_repeatable_runs", task_id=job["id"])] == [None]


def _accuracy(user) -> float:
	return db.row("users", id=user["id"])["volunteer_janitor_correctness"]


def _verdict(comment) -> str:
	'''The moderators' verdict on `comment`, as a lone volunteer's Ban rating of it shows.'''
	volunteer = factories.user()
	_rate(volunteer, comment, "Ban")
	_recalc()
	accuracy = _accuracy(volunteer)
	for verdict, expected in (("bad", RIGHT), ("not bad", WRONG), ("ignored", UNTRAINED)):
		if accuracy == pytest.approx(expected, abs=1e-12):
			return verdict
	raise AssertionError(f"accuracy {accuracy} matches no verdict")


@pytest.mark.parametrize("via", ["command", "job"])
@pytest.mark.parametrize("judged_bad", [True, False], ids=["bad", "not bad"])
@pytest.mark.parametrize("result", SAYS)
def test_a_lone_volunteers_accuracy_from_one_rating(result, judged_bad, via):
	volunteer = factories.user()
	_rate(volunteer, _judged(judged_bad), result)

	_recalc(via)

	assert _accuracy(volunteer) == pytest.approx(_lone(judged_bad, result), abs=1e-12)


def test_the_stored_accuracy_plays_no_part():
	volunteer = factories.user(volunteer_janitor_correctness=0.9)
	_rate(volunteer, _bad(), "Ban")

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(RIGHT, abs=1e-12)


@pytest.mark.parametrize("level", [1, 3])
def test_an_admins_rating_weighs_4_times_its_confidence(level):
	ban, neutral, unclear = factories.admin(level), factories.admin(level), factories.admin(level)
	_rate(ban, _bad(), "Ban")
	_rate(neutral, _comment(), "Neutral")
	_rate(unclear, _comment(), "Ban")

	_recalc()

	# Ban on a bad comment: W = B = 4 + 4, so the estimate is 8.5 / 9
	s = (8.5 / 9 - 0.5 - 0.1) / 0.4
	assert _accuracy(ban) == pytest.approx(_after_100_rounds((0.4 + s) / (2 + s)), abs=1e-12)
	# Neutral on one not bad: W = 4 + 4 × 0.5, B = 0, so the estimate is 0.5 / 7
	k = 0.5 * (0.5 - 0.5 / 7 - 0.1) / 0.4
	assert _accuracy(neutral) == pytest.approx(_after_100_rounds((0.4 + k) / (2 + k)), abs=1e-12)
	# Ban on one not bad: W = 8, B = 4, so the estimate is exactly 0.5 and teaches nothing
	assert _accuracy(unclear) == pytest.approx(UNTRAINED, abs=1e-12)


@pytest.mark.parametrize("result", SAYS)
def test_ratings_of_ignored_comments_teach_nothing(result):
	volunteer = factories.user()
	_rate(volunteer, _ignored(), result)

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(UNTRAINED, abs=1e-12)


def test_several_ratings_add_up():
	volunteer = factories.user()
	for judged_bad, result in ((True, "Ban"), (False, "Good"), (False, "Ban"), (True, "Bad")):
		_rate(volunteer, _judged(judged_bad), result)

	_recalc()

	# Three right (k = 0.75, 0.75, 0.375) and one wrong (k = 0.75); the volunteer's weight stays 0
	assert _accuracy(volunteer) == pytest.approx(_after_100_rounds((0.4 + 1.875) / (2 + 2.625)), abs=1e-12)


@pytest.mark.parametrize("offset, verdict", [(-899, "bad"), (899, "bad"), (-900, "not bad"), (900, "not bad"), (-899.5, "not bad"), (899.5, "bad")])
def test_a_note_counts_with_a_distinguished_reply_less_than_15_minutes_away(offset, verdict):
	# Note times are rounded down to the second
	comment = _comment()
	_reply(comment)
	factories.note(_author(comment), "Warning", REPLY + timedelta(seconds=offset))

	assert _verdict(comment) == verdict


@pytest.mark.parametrize("after, verdict", [(timedelta(hours=47, minutes=59, seconds=59), "ignored"), (timedelta(hours=48), "not bad"), (timedelta(seconds=1), "ignored"), (timedelta(seconds=0.5), "not bad"), (timedelta(0), "not bad"), (-timedelta(hours=1), "not bad")])
def test_a_note_within_48_hours_after_the_comment_has_it_ignored(after, verdict):
	comment = _comment()
	factories.note(_author(comment), "Warning", T0 + after)

	assert _verdict(comment) == verdict


@pytest.mark.parametrize("tag, verdict", [*((tag, "bad") for tag in NEGATIVE), ("Quality", "not bad"), ("Good", "not bad"), ("Comment", "not bad")])
def test_only_negative_notes_count(tag, verdict):
	comment = _comment()
	_reply(comment)
	factories.note(_author(comment), tag, REPLY)

	assert _verdict(comment) == verdict


@pytest.mark.parametrize("tag", ["Comment", "Warning"])
def test_only_negative_notes_have_a_comment_ignored(tag):
	comment = _comment()
	factories.note(_author(comment), tag, T0 + timedelta(hours=1))

	assert _verdict(comment) == ("ignored" if tag == "Warning" else "not bad")


@pytest.mark.parametrize("near_first", [True, False], ids=["near reply first", "far reply first"])
def test_any_distinguished_reply_near_a_note_makes_a_comment_bad(near_first):
	comment = _comment()
	for at in ((REPLY, REPLY + timedelta(hours=1)) if near_first else (REPLY + timedelta(hours=1), REPLY)):
		_reply(comment, at=at)
	factories.note(_author(comment), "Warning", REPLY)

	assert _verdict(comment) == "bad"


@pytest.mark.parametrize("near_first", [True, False], ids=["near note first", "far note first"])
def test_any_negative_note_near_a_distinguished_reply_makes_a_comment_bad(near_first):
	comment = _comment()
	_reply(comment)
	for at in ((REPLY, REPLY + timedelta(hours=1)) if near_first else (REPLY + timedelta(hours=1), REPLY)):
		factories.note(_author(comment), "Warning", at)

	assert _verdict(comment) == "bad"


def test_a_note_about_someone_else_doesnt_count():
	comment = _comment()
	_reply(comment)
	factories.note(factories.user(), "Warning", REPLY)

	assert _verdict(comment) == "not bad"


def test_a_note_counts_whatever_comment_it_names():
	comment = _comment()
	_reply(comment)
	factories.note(_author(comment), "Warning", REPLY, reference_comment=_comment(author=_author(comment))["id"])

	assert _verdict(comment) == "bad"


def test_only_a_distinguished_direct_reply_counts():
	undistinguished, nested = _comment(), _comment()
	_reply(undistinguished, distinguish_level=0)
	_reply(_reply(nested, distinguish_level=0))
	for comment in (undistinguished, nested):
		factories.note(_author(comment), "Warning", REPLY)

	assert (_verdict(undistinguished), _verdict(nested)) == ("not bad", "not bad")


def test_a_reply_with_a_note_makes_a_comment_bad_even_within_48_hours():
	comment = _comment()
	_reply(comment, at=T0 + timedelta(hours=1))
	factories.note(_author(comment), "Warning", T0 + timedelta(hours=1))

	assert _verdict(comment) == "bad"


def test_deleted_comments_teach_nothing():
	volunteer = factories.user()
	_rate(volunteer, _bad(state_user_deleted_utc="2024-01-02T00:00:00Z"), "Good")
	_rate(volunteer, _bad(), "Ban")

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(RIGHT, abs=1e-12)


def test_only_the_first_rating_after_the_assignment_counts():
	volunteer = factories.user()
	unassigned, rated = _bad(), _bad()
	factories.rating(volunteer, unassigned, "Good")
	_rate(volunteer, rated, "Ban")
	factories.rating(volunteer, rated, "Good")

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(RIGHT, abs=1e-12)


@pytest.mark.parametrize("sequence", [["Pending", "Ban", "Pending"], ["Pending", "Pending", "Ban"], ["Good", "Pending", "Ban"], ["Pending", "Ban", "Good"]])
def test_the_first_rating_after_an_assignment_counts_whatever_else_was_stored(sequence):
	volunteer = factories.user()
	comment = _bad()
	for minute, result in enumerate(sequence):
		at = T0 + timedelta(minutes=minute)
		factories.assignment(volunteer, comment, at=at) if result == "Pending" else factories.rating(volunteer, comment, result, at=at)

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(RIGHT, abs=1e-12)


@pytest.mark.parametrize("first, expected", [("Ban", RIGHT), ("Good", WRONG)])
def test_of_two_ratings_stored_at_once_the_first_stored_counts(first, expected):
	volunteer = factories.user()
	comment = _bad()
	factories.assignment(volunteer, comment, at=T0)
	for result in (first, "Good" if first == "Ban" else "Ban"):
		factories.rating(volunteer, comment, result, at=T0 + timedelta(minutes=1))

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(expected, abs=1e-12)


def test_a_shadowbanned_volunteers_ratings_move_no_estimate_but_their_accuracy_is_worked_out():
	shadowbanned, volunteer = factories.admin(2, shadowbanned="somemod"), factories.user()
	comment = _comment()
	_rate(shadowbanned, comment, "Ban")
	_rate(volunteer, comment, "Ban")

	_recalc()

	# Counted, the admin's weight of 4 would make the estimate exactly 0.5 and teach nothing; left out, it stays 0.1
	assert (_accuracy(shadowbanned), _accuracy(volunteer)) == pytest.approx((WRONG, WRONG), abs=1e-12)


@pytest.mark.parametrize("rating", ["of a deleted comment", "without an assignment"])
def test_a_volunteer_whose_ratings_teach_nothing_starts_over(rating):
	volunteer = factories.user(volunteer_janitor_correctness=0.9)
	if rating == "of a deleted comment":
		_rate(volunteer, _bad(state_user_deleted_utc="2024-01-02T00:00:00Z"), "Ban")
	else:
		factories.rating(volunteer, _bad(), "Ban")

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(UNTRAINED, abs=1e-12)


def test_a_volunteer_who_never_rated_keeps_their_accuracy():
	volunteer = factories.user(volunteer_janitor_correctness=0.9)
	factories.assignment(volunteer, _bad())

	with db_diff() as d:
		_recalc()

	d.assert_exactly()


@pytest.mark.parametrize("missed", ["bad", "not bad", "ignored"])
def test_an_assignment_never_rated_costs_nothing(missed):
	volunteer = factories.user()
	_rate(volunteer, _bad(), "Ban")
	factories.assignment(volunteer, {"bad": _bad, "not bad": _comment, "ignored": _ignored}[missed]())

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(RIGHT, abs=1e-12)


# Pinned as they are; see spec/AUDITS.md


def test_a_comment_the_moderators_removed_still_teaches():
	volunteer = factories.user()
	_rate(volunteer, _bad(state_mod="REMOVED", state_mod_set_by="somemod"), "Ban")

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(RIGHT, abs=1e-12)


def test_a_deleted_distinguished_reply_still_counts():
	comment = _comment()
	_reply(comment, state_user_deleted_utc="2024-01-04T00:00:00Z")
	factories.note(_author(comment), "Warning", REPLY)

	assert _verdict(comment) == "bad"


def test_a_suspended_volunteer_still_learns():
	volunteer = factories.user(is_banned=factories.admin(2)["id"], unban_utc=0)
	_rate(volunteer, _bad(), "Ban")

	_recalc()

	assert _accuracy(volunteer) == pytest.approx(RIGHT, abs=1e-12)


def test_a_comment_by_a_since_shadowbanned_author_still_teaches():
	assert _verdict(_bad(author=factories.user(shadowbanned="somemod"))) == "bad"


def test_accuracies_feed_back_through_the_estimates():
	# Expected values checked against a model written from this docstring alone
	accurate, sloppy, admin = factories.user(), factories.user(), factories.admin(2)
	comments = [_bad(), _comment(), _comment(), _bad(), _ignored(), _comment()]
	ratings = [
		(accurate, ["Ban", "Good", "TopQuality", "Warning", "Bad", "Good"]),
		(sloppy, ["Good", "Neutral", None, "Bad", "Good", "Ban"]),
		(admin, [None, None, "Bad", "Ban", None, None]),
	]
	for volunteer, results in ratings:
		for comment, result in zip(comments, results):
			if result: _rate(volunteer, comment, result)

	_recalc()

	assert [_accuracy(v) for v in (accurate, sloppy, admin)] == pytest.approx([0.6996897121052889, 0.27963858112309226, 0.43027174112208855], abs=1e-12)
