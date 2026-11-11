'''
In the default profile, which has no hCaptcha site key, no page loads hCaptcha's script: the forms that would ask for an answer don't (auth/test_signup.py, notifications/test_modmail.py).
'''
import pytest

from files.tests.spec.harness import *
from files.tests.spec.harness import captcha


@pytest.mark.parametrize("path", ["/signup", "/contact", "/press", "/media"])
def test_the_forms_dont_load_hcaptcha(path):
	r = anon().get(path)

	assert_html(r, 200)
	assert_not_in_payload(r, captcha.WIDGET_SCRIPT)
