'''
hCaptcha, as the site meets it in the `captcha` deployment profile (config.PROFILES), which gives it a site key and a secret (hCaptcha's published test pair). spec/captcha/ specifies it.

With a site key, signing up and the contact form for visitors (not logged in) ask for an hCaptcha answer. Their pages load hCaptcha's script (WIDGET_SCRIPT) and carry the site key, for the widget it draws, and the answer arrives as the form field FIELD. The site checks the answer by POSTing a form to either of hCaptcha's SITEVERIFY addresses, holding "secret", "response" (the answer) and "sitekey"; it may send hCaptcha's optional fields as well. It accepts the answer only when the reply has status 200 and is a JSON object whose "success" is true. Everything else refuses: a missing or empty answer (without asking hCaptcha), hCaptcha's refusal, and an answer the site can't check (FAILURES).
'''
import json
from urllib.parse import parse_qsl

from files.tests.spec.harness import config, external_web

SITE_KEY = config.PROFILES["captcha"]["HCAPTCHA_SITEKEY"]
SECRET = config.PROFILES["captcha"]["HCAPTCHA_SECRET"]
SITEVERIFY = ("https://api.hcaptcha.com/siteverify", "https://hcaptcha.com/siteverify")
WIDGET_SCRIPT = "https://js.hcaptcha.com/1/api.js"
FIELD = "h-captcha-response"

_JSON = {"Content-Type": "application/json"}

# Replies no verdict can be read from
_UNREADABLE = {
	"not JSON": "<html>busy</html>",
	"no verdict": "{}",
	"a verdict that's a string": '{"success": "false"}',
	"a verdict that's a number": '{"success": 1}',
	"a JSON array": "[]",
	"JSON null": "null",
	"a bare JSON value": "5",
}

FAILURES = ("unreachable", "untrusted certificate", "an error status", *_UNREADABLE)
'''Ways checking an answer can fail (fail), each of which refuses it. An untrusted certificate and an error status come with a reply approving the answer, which the site mustn't heed.'''


def _reply(success: bool) -> str:
	return json.dumps({"success": success, "challenge_ts": "2031-01-01T00:00:00.000Z", "hostname": config.site_host()})


def answer(success: bool):
	'''hCaptcha's verdict on every answer the site checks from now on.'''
	for url in SITEVERIFY:
		external_web.serve(url, method="POST", headers=_JSON, body=_reply(success))


def fail(how: str):
	'''Checking an answer fails from now on, in the way FAILURES names. An untrusted certificate, and an error status, come with a reply approving the answer: a site checking certificates, as it must, never reads the first, and a reply that isn't a 200 holds no verdict.'''
	for url in SITEVERIFY:
		if how == "unreachable":
			external_web.unreachable(url, method="POST")
		elif how == "untrusted certificate":
			external_web.serve(url, method="POST", headers=_JSON, body=_reply(True), trusted=False)
		elif how == "an error status":
			external_web.serve(url, method="POST", status=500, headers=_JSON, body=_reply(True))
		else:
			external_web.serve(url, method="POST", headers=_JSON, body=_UNREADABLE[how])


def verifications() -> list[dict]:
	'''The forms the site sent to the SITEVERIFY addresses so far.'''
	return [dict(parse_qsl(body.decode())) for url in SITEVERIFY for body in external_web.request_bodies(url, method="POST")]


def assert_checked(response: str):
	'''The site checked the answer `response` with hCaptcha, once, as the site it is.'''
	forms = verifications()
	assert len(forms) == 1, f"expected one check with hCaptcha, got {forms}"
	assert {name: forms[0].get(name) for name in ("secret", "response", "sitekey")} == {"secret": SECRET, "response": response, "sitekey": SITE_KEY}
