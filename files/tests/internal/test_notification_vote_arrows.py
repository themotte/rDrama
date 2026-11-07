'''
The notification page marks the viewer's own votes on the arrows of the comments it shows. Which arrow is marked is markup, outside the spec's page contract, so it's checked here.
'''
import re

import pytest

from files.tests.spec.harness import as_user, factories


@pytest.mark.parametrize("vote, arrow", [(1, "up"), (-1, "down")])
def test_the_viewers_vote_is_marked(vote, arrow):
	user = factories.user()
	post = factories.post(user)
	reply = factories.comment(factories.user(), post, parent=factories.comment(user, post))
	factories.notification(user, reply)
	factories.vote(user, reply, vote)

	page = as_user(user).get("/notifications").text

	marked = {direction for direction in ("up", "down") if re.search(rf'class="comment-{reply["id"]}-{direction} [^"]*\bactive\b', page)}
	assert marked == {arrow}
