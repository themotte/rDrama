'''The admin charts' data (the charts themselves are images, which the spec can only see served).'''
import sys
import time

import pytest
from flask import g

import files.routes.static  # noqa: F401  (the module, not a route function of the same package name)
from files.__main__ import app, db_session
from files.tests.spec.harness import factories, seed

static = sys.modules["files.routes.static"]

# A UTC midnight well after anything the seed holds (and inside the int4 timestamp columns); the day so far is three hours
MIDNIGHT = 2_000_000_000 // 86400 * 86400
NOW = MIDNIGHT + 3 * 3600
DAY = 86400


def _series(kind):
	with app.test_request_context("/"):
		g.db = db_session()
		return static._chart_series(kind, NOW)


@pytest.mark.parametrize("kind, span", [("daily", DAY), ("weekly", 7 * DAY)])
def test_the_points_are_the_whole_spans_before_today(kind, span):
	labels, *_ = _series(kind)

	assert len(labels) == 46
	assert labels == [time.strftime("%d/%m", time.gmtime(MIDNIGHT - span * i)) for i in range(46, 0, -1)]


@pytest.mark.parametrize("kind, span", [("daily", DAY), ("weekly", 7 * DAY)])
def test_each_row_counts_in_the_span_it_was_created_in(kind, span):
	oldest = MIDNIGHT - 46 * span
	for created in (oldest - 1, oldest, oldest + span - 1, MIDNIGHT - span, MIDNIGHT - 1, MIDNIGHT, NOW):
		factories.user(created_utc=created)

	_, signups, _, _ = _series(kind)

	assert signups[0] == 2 and signups[-1] == 2 and sum(signups) == 4


def test_posts_and_comments_count_only_if_visible_and_not_by_the_system():
	author = factories.user(created_utc=0)
	post = factories.post(author, created_utc=MIDNIGHT - 1)
	factories.post(author, created_utc=MIDNIGHT - 1)
	factories.post(author, created_utc=MIDNIGHT - 1, state_mod="REMOVED", state_mod_set_by="somemod")
	for _ in range(2): factories.comment(author, post, created_utc=MIDNIGHT - 1)
	factories.comment(author, post, created_utc=MIDNIGHT - 1, state_mod="REMOVED", state_mod_set_by="somemod")
	factories.comment({"id": seed.AUTOJANNY_ID}, post, created_utc=MIDNIGHT - 1)

	_, _, posts, comments = _series("daily")

	assert posts[-1] == 2 and comments[-1] == 2


def test_a_new_day_draws_a_new_chart():
	factories.user(created_utc=MIDNIGHT)

	with app.test_request_context("/"):
		g.db = db_session()
		before, after = static._chart_png("daily", MIDNIGHT), static._chart_png("daily", MIDNIGHT + DAY)

	assert before != after
