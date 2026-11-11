'''
With the limits on, a signup sent within 5 seconds of its form is refused, as one too quick for a person. The form's time is in whole seconds of the limits' clock (harness.limit_clock_set).
'''
from datetime import timedelta

import pytest

from files.tests.spec.harness import *
from files.tests.spec.harness.limits import T0

pytestmark = pytest.mark.profile("limits")


def _form(at):
	limit_clock_set(at)
	client = anon()
	return client, client.get("/signup")


def _signup(client, form, at, **fields):
	limit_clock_set(at)
	username = factories.unique("new")
	r = client.post_raw("/signup", {"formkey": form.form_field("formkey"), "now": form.form_field("now"), "usernametwo": username, "email": "", "password": factories.PASSWORD, "password_confirm": factories.PASSWORD, **fields})
	return r, username


def test_a_signup_sent_too_soon_after_its_form_is_refused():
	factories.user()
	client, form = _form(T0)

	with db_diff() as d:
		r, _ = _signup(client, form, T0 + timedelta(seconds=4.9))

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()


@pytest.mark.parametrize(("issued", "sent"), [(0, 5), (0.9, 5)], ids=["5 seconds later", "the form's time rounded down"])
def test_a_signup_sent_5_seconds_after_its_form_goes_through(issued, sent):
	factories.user()
	client, form = _form(T0 + timedelta(seconds=issued))

	r, username = _signup(client, form, T0 + timedelta(seconds=sent))

	assert_status(r, 302)
	assert db.row("users", username=username)


@pytest.mark.parametrize("now", ["soon", "²"])
def test_a_form_time_that_is_not_a_number_is_refused(now):
	factories.user()
	client, form = _form(T0)

	with db_diff() as d:
		r, _ = _signup(client, form, T0 + timedelta(seconds=10), now=now)

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()
