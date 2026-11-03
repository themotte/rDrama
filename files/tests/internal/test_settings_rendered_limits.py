'''
Profile text fields also cap their rendered HTML. The cap depends on the exact markup the sanitizer emits, which isn't part of the spec, so these live outside it.
'''
from files.tests.spec.harness import *

# Bare URLs render to links several times their length
LINKS_1500_CHARS = "http://a.co " * 125
LINKS_500_CHARS = "http://a.co " * 41


def test_bio_rendering_to_over_10000_characters_is_refused():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/profile", {"bio": LINKS_1500_CHARS})

	assert_html(r, 200)
	d.assert_exactly()


def test_friends_list_rendering_to_over_2000_characters_is_refused():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/profile", {"friends": LINKS_500_CHARS})

	assert_html(r, 200)
	d.assert_exactly()
