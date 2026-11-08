'''
Volunteer janitor duty: logged-in users are asked to rate reported comments.

GET /volunteer gives the visitor a duty when one is available: up to 3 eligible comments, chosen at random, each assigned to them to rate (a "volunteer_janitor" row with result "Pending"), and their "volunteer_last_started_utc" set to now. The page shows the assigned comments' text and the rating form (see test_ratings; its fields name the comments by id), and nothing else about the comments: not who wrote them, not the post or thread they are in (nor a link to it), not their reports or what volunteers made of them so far (not even to admins), and no actions on them. With nothing available the page says so and nothing is written. Anonymous visitors are sent to log in; API clients are refused (403), changing nothing.

A visitor has no duty available within 20 hours of their last start.

A comment is eligible for a volunteer when:
- its reports are open (REPORTED);
- it is visible: not removed, not held for review, not deleted by its author;
- it is neither the volunteer's own comment nor a reply to one of theirs;
- none of its direct replies is distinguished (an admin speaking officially);
- someone other than the volunteer reported it;
- the volunteer was never assigned it before.

A post's page shows a link to /volunteer exactly when a duty is available to the viewer.
'''
import pytest

from files.tests.spec.harness import *


def _eligible(**overrides):
	'''A comment any fresh volunteer may be given, unless `overrides` say otherwise.'''
	comment = factories.comment(factories.user(), factories.post(factories.user()), **{"state_report": "REPORTED", **overrides})
	factories.report(factories.user(), comment)
	return comment


def _started(volunteer, hours_ago):
	db.execute("UPDATE users SET volunteer_last_started_utc = now() - :hours * interval '1 hour' WHERE id = :id", hours=hours_ago, id=volunteer["id"])


def _assigned(volunteer, comment):
	return {"user_id": volunteer["id"], "comment_id": comment["id"], "result": "Pending"}


def test_a_volunteer_is_assigned_an_eligible_comment():
	comment = _eligible()
	volunteer = factories.user()

	with db_diff() as d:
		r = as_user(volunteer).get("/volunteer")

	assert_html(r, 200)
	assert_in_payload(r, comment["body"])
	d.assert_exactly(inserted={"volunteer_janitor": [_assigned(volunteer, comment)]}, updated={"users": {volunteer["id"]: {"volunteer_last_started_utc": ANY}}})
	assert db.execute("SELECT now() - volunteer_last_started_utc < interval '1 minute' FROM users WHERE id = :id", id=volunteer["id"])


@pytest.mark.parametrize("volunteer_level", [0, 2])
def test_the_page_shows_only_the_comments_text(volunteer_level):
	post = factories.post(factories.user())
	author, reporter = factories.user(), factories.user()
	comment = factories.comment(author, post, state_report="REPORTED")
	reason = factories.report(reporter, comment)["reason"]

	r = as_user(factories.admin(volunteer_level)).get("/volunteer")

	assert_in_payload(r, comment["body"])
	for hidden in (author["username"], post["title"], f"/post/{post['id']}", f"/comment/{comment['id']}", reporter["username"], reason):
		assert_not_in_payload(r, hidden)


def test_a_duty_holds_at_most_three_comments():
	comments = [_eligible() for _ in range(4)]
	volunteer = factories.user()

	as_user(volunteer).get("/volunteer")

	assigned = {row["comment_id"] for row in db.rows("volunteer_janitor", user_id=volunteer["id"])}
	assert len(assigned) == 3 and assigned <= {c["id"] for c in comments}


def test_without_eligible_comments_nothing_is_assigned():
	_eligible(state_report="RESOLVED")
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.get("/volunteer")

	assert_html(r, 200)
	d.assert_exactly()


@pytest.mark.parametrize("hours, assigned", [(19.5, False), (20.5, True)])
def test_a_new_duty_comes_20_hours_after_the_last(hours, assigned):
	comment = _eligible()
	volunteer = factories.user()
	_started(volunteer, hours)

	r = as_user(volunteer).get("/volunteer")

	assert_html(r, 200)
	assert bool(db.rows("volunteer_janitor", user_id=volunteer["id"])) == assigned
	(assert_in_payload if assigned else assert_not_in_payload)(r, comment["body"])


def test_visitors_are_sent_to_log_in():
	assert_login_redirect(anon().get("/volunteer"), "/volunteer")


# Eligibility

def _own(volunteer):
	return _eligible(author_id=volunteer["id"])


def _reply_to_own(volunteer):
	post = factories.post(factories.user())
	parent = factories.comment(volunteer, post)
	reply = factories.comment(factories.user(), post, parent, state_report="REPORTED")
	factories.report(factories.user(), reply)
	return reply


def _officially_answered(volunteer):
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post, state_report="REPORTED")
	factories.report(factories.user(), comment)
	factories.comment(factories.admin(2), post, comment, distinguish_level=1)
	return comment


def _reported_only_by_the_volunteer(volunteer):
	comment = factories.comment(factories.user(), factories.post(factories.user()), state_report="REPORTED")
	factories.report(volunteer, comment)
	return comment


def _unreported_but_open(volunteer):
	return factories.comment(factories.user(), factories.post(factories.user()), state_report="REPORTED")


def _assigned_before(volunteer):
	comment = _eligible()
	factories.assignment(volunteer, comment)
	return comment


def _rated_before(volunteer):
	comment = _eligible()
	db.insert("volunteer_janitor", user_id=volunteer["id"], comment_id=comment["id"], result="Good")
	return comment


INELIGIBLE = {
	"reports never opened": lambda v: _eligible(state_report="UNREPORTED"),
	"reports resolved": lambda v: _eligible(state_report="RESOLVED"),
	"reports ignored": lambda v: _eligible(state_report="IGNORED"),
	"removed": lambda v: _eligible(state_mod="REMOVED"),
	"held": lambda v: _eligible(state_mod="FILTERED"),
	"deleted": lambda v: _eligible(state_user_deleted_utc="2020-01-01T00:00:00Z"),
	"own comment": _own,
	"reply to own comment": _reply_to_own,
	"distinguished reply": _officially_answered,
	"reported only by the volunteer": _reported_only_by_the_volunteer,
	"no report stored": _unreported_but_open,
	"assigned before": _assigned_before,
	"rated before": _rated_before,
}


@pytest.mark.parametrize("case", INELIGIBLE)
def test_ineligible_comments_are_never_assigned(case):
	volunteer = factories.user()
	INELIGIBLE[case](volunteer)

	with db_diff() as d:
		r = as_user(volunteer).get("/volunteer")

	assert_html(r, 200)
	d.assert_exactly()


def test_others_assignments_dont_matter():
	comment = _eligible()
	factories.assignment(factories.user(), comment)
	volunteer = factories.user()

	as_user(volunteer).get("/volunteer")

	assert [row["comment_id"] for row in db.rows("volunteer_janitor", user_id=volunteer["id"])] == [comment["id"]]


# The invitation

def test_a_posts_page_invites_viewers_with_a_duty_available():
	_eligible()
	post = factories.post(factories.user())

	r = as_user(factories.user()).get(f"/post/{post['id']}")

	assert_in_payload(r, 'href="/volunteer"')


@pytest.mark.parametrize("why", ["nothing to do", "recent duty"])
def test_a_posts_page_doesnt_invite_viewers_without_one(why):
	viewer = factories.user()
	if why == "recent duty":
		_eligible()
		_started(viewer, 1)
	post = factories.post(factories.user())

	r = as_user(viewer).get(f"/post/{post['id']}")

	assert_html(r, 200)
	assert_not_in_payload(r, 'href="/volunteer"')
