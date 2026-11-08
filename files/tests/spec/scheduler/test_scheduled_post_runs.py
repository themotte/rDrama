'''
What the scheduled-task worker makes when a scheduled post (see spec/admin/test_scheduled_posts.py) runs: a new post each run, as if its author (`author_id_submission`) had submitted it at the run's time.

The post (with `task_id` naming the scheduled post) takes the scheduled post's url, body, body_html, flair, ghost, private (a private one makes a draft) and over_18. Its title is the scheduled post's with Python strftime codes (`%Y`, `%m`, `%d`, `%B`, `%A`, ...; C locale) filled in from the run's start time in UTC, and its `created_utc` is that time. As for a submitted post: its author's own upvote counts unless they're shadowbanned, their post count follows, mentioned users and the author's followers are notified unless it's a draft or a ghost post, and a link to a web address (not an upload on the site) gets its thumbnail fetched in the background (spec/posts/test_fetchers.py). An author's suspension doesn't stop their scheduled posts.

A scheduled post's page lists the posts it made.
'''
import calendar
from datetime import datetime, timedelta, timezone

import pytest

from files.tests.spec.harness import *

MONDAY = 1 << 2
SLOT = datetime(2024, 1, 8, 8, 0, tzinfo=timezone.utc)
'''A Monday 08:00 UTC.'''
CREATED = calendar.timegm((2024, 1, 2, 0, 0, 0))
'''A Tuesday, after the Monday slot before SLOT.'''


def _scheduled(author, **overrides):
	return factories.scheduled_post(author, **{"frequency_day": MONDAY, "time_of_day_utc": "08:00", "created_utc": CREATED, **overrides})


def test_a_run_posts_the_scheduled_post_as_its_author_at_the_run_time():
	author = factories.admin(2)
	scheduled = _scheduled(author, title="Thread for %A %d %B %Y (%m)", url="https://example.com/a", flair="Weekly", over_18=True)

	with db_diff() as d:
		run_scheduler(SLOT)

	[post] = d.inserted["submissions"]
	d.assert_exactly(
		inserted={
			"submissions": [{"author_id": author["id"], "task_id": scheduled["id"], "title": "Thread for Monday 08 January 2024 (01)", "url": "https://example.com/a", "body": scheduled["body"], "body_html": scheduled["body_html"], "flair": "Weekly", "ghost": False, "private": False, "over_18": True, "created_utc": calendar.timegm(SLOT.utctimetuple()), "state_mod": "VISIBLE", "upvotes": 1, "realupvotes": 1, "downvotes": 0}],
			"votes": [{"user_id": author["id"], "submission_id": post["id"], "vote_type": 1, "real": True}],
			"tasks_repeatable_runs": [{"task_id": scheduled["id"]}],
		},
		updated={
			"tasks_repeatable": {scheduled["id"]: {"run_time_last": SLOT.replace(tzinfo=None)}},
			"users": {author["id"]: {"post_count": 1}},
		},
	)


def test_each_run_makes_a_new_post():
	scheduled = _scheduled(factories.admin(2))

	run_scheduler(SLOT)
	run_scheduler(SLOT + timedelta(days=7))

	assert [p["created_utc"] for p in db.rows("submissions", task_id=scheduled["id"])] == [calendar.timegm(at.utctimetuple()) for at in (SLOT, SLOT + timedelta(days=7))]


def test_mentioned_users_and_followers_are_notified():
	author, mentioned, follower = factories.admin(2), factories.user(), factories.user()
	db.insert("follows", user_id=follower["id"], target_id=author["id"])
	_scheduled(author, body=f"hello @{mentioned['username']}")

	run_scheduler(SLOT)

	assert sorted(n["user_id"] for n in db.rows("notifications")) == sorted([mentioned["id"], follower["id"]])


@pytest.mark.parametrize("kind", ["private", "ghost"])
def test_drafts_and_ghost_posts_notify_nobody(kind):
	author, mentioned, follower = factories.admin(2), factories.user(), factories.user()
	db.insert("follows", user_id=follower["id"], target_id=author["id"])
	scheduled = _scheduled(author, body=f"hello @{mentioned['username']}", **{kind: True})

	run_scheduler(SLOT)

	[post] = db.rows("submissions", task_id=scheduled["id"])
	assert post[kind] is True
	assert db.rows("notifications") == []


def test_a_shadowbanned_authors_own_upvote_doesnt_count():
	author = factories.admin(2, shadowbanned="somemod")
	scheduled = _scheduled(author)

	run_scheduler(SLOT)

	[post] = db.rows("submissions", task_id=scheduled["id"])
	assert (post["upvotes"], post["realupvotes"], db.row("votes", submission_id=post["id"])["real"]) == (0, 0, False)


def test_a_suspended_authors_scheduled_post_still_posts():
	author = factories.admin(2, is_banned=factories.admin(3)["id"], unban_utc=0)
	scheduled = _scheduled(author)

	run_scheduler(SLOT)

	assert len(db.rows("submissions", task_id=scheduled["id"])) == 1


def test_the_scheduled_posts_page_lists_the_posts_it_made():
	admin = factories.admin(2)
	scheduled = _scheduled(admin)
	run_scheduler(SLOT)
	[post] = db.rows("submissions", task_id=scheduled["id"])

	r = as_user(admin).get(f"/tasks/scheduled_posts/{scheduled['id']}")

	assert_html(r, 200)
	assert_in_payload(r, f'id="post-{post["id"]}"')


def test_a_scheduled_link_post_gets_a_thumbnail_like_a_submitted_one():
	external_web.serve("https://example.com/article", headers={"Content-Type": "text/html"}, body='<html><head><meta property="og:image" content="https://cdn.example.com/preview.png"></head></html>')
	external_web.serve("https://cdn.example.com/preview.png", headers={"Content-Type": "image/png"}, body=uploads.png(64, 64)[1])
	scheduled = _scheduled(factories.admin(2), url="https://example.com/article")

	run_scheduler(SLOT)
	run_background_work()

	[post] = db.rows("submissions", task_id=scheduled["id"])
	assert post["thumburl"].startswith("/images/")
	assert_serves_image(post["thumburl"])
