'''
With a site key, the signup form asks for an hCaptcha answer, and a signup is created only once hCaptcha approves its answer; otherwise it goes back to the form with an "error", as other refused signups do (auth/test_signup.py).
'''
import pytest

from files.tests.spec.harness import *
from files.tests.spec.harness import captcha

pytestmark = pytest.mark.profile("captcha")


def _signup(client, **fields):
	form = client.get("/signup")
	return client.post_raw("/signup", {"formkey": form.form_field("formkey"), "now": form.form_field("now"), "usernametwo": factories.unique("new"), "email": "", "password": factories.PASSWORD, "password_confirm": factories.PASSWORD, **fields})


@pytest.fixture(autouse=True)
def an_existing_member():
	'''The first signup on a site holding only the system accounts is special (auth/test_signup.py), so these start with a member present.'''
	return factories.user()


def test_the_form_offers_the_captcha():
	r = anon().get("/signup")

	assert_html(r, 200)
	assert_in_payload(r, captcha.SITE_KEY)
	assert_in_payload(r, captcha.WIDGET_SCRIPT)


def test_a_signup_hcaptcha_approves_is_created():
	captcha.answer(True)
	client, username, answer = anon(), factories.unique("new"), factories.unique("answer")

	r = _signup(client, usernametwo=username, **{captcha.FIELD: answer})

	assert_redirect(r, "")
	assert client.user_id == db.row("users", username=username)["id"]
	captcha.assert_checked(answer)


def test_a_signup_hcaptcha_refuses_is_refused():
	captcha.answer(False)
	answer = factories.unique("answer")

	with db_diff() as d:
		r = _signup(anon(), **{captcha.FIELD: answer})

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()
	captcha.assert_checked(answer)


@pytest.mark.parametrize("fields", [{}, {captcha.FIELD: ""}], ids=["absent", "empty"])
def test_a_signup_without_an_answer_is_refused_without_asking(fields):
	captcha.answer(True)

	with db_diff() as d:
		r = _signup(anon(), **fields)

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()
	assert external_web.requests() == []


@pytest.mark.parametrize("failure", captcha.FAILURES)
def test_a_signup_whose_answer_cant_be_checked_is_refused(failure):
	captcha.fail(failure)

	with db_diff() as d:
		r = _signup(anon(), **{captcha.FIELD: factories.unique("answer")})

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()
