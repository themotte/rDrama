'''The captcha profile reaching the app in-process, and the site's report of an answer it couldn't check with hCaptcha.'''
import os

import pytest

from files.helpers.captcha import validate_captcha
from files.helpers.config import environment
from files.tests.spec.harness import backend_inprocess, captcha


def test_the_captcha_profile_sets_the_keys_for_its_tests():
	backend_inprocess.reset("captcha")
	assert (environment.HCAPTCHA_SITEKEY, environment.HCAPTCHA_SECRET) == (captcha.SITE_KEY, captcha.SECRET)

	backend_inprocess.reset(None)
	assert (environment.HCAPTCHA_SITEKEY, environment.HCAPTCHA_SECRET) == (os.environ.get("HCAPTCHA_SITEKEY", "").strip(), os.environ.get("HCAPTCHA_SECRET", "").strip())


@pytest.mark.parametrize("failure", captcha.FAILURES)
def test_an_answer_that_cant_be_checked_is_reported(failure, capsys):
	backend_inprocess.reset("captcha")
	captcha.fail(failure)

	assert validate_captcha("answer") is False
	assert "[captcha]" in capsys.readouterr().err
