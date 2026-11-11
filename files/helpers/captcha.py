import sys
from typing import Final
import requests

from files.helpers.config import environment
from files.helpers.config.environment import OUTBOUND_VERIFY

HCAPTCHA_URL: Final[str] = "https://hcaptcha.com/siteverify"


def site_key() -> str:
	'''The site's hCaptcha site key; without one, no captcha is asked.'''
	return environment.HCAPTCHA_SITEKEY


def validate_captcha(token: str):
	sitekey = site_key()
	if not sitekey: return True
	if not token: return False
	data = {"secret": environment.HCAPTCHA_SECRET,
			"response": token,
			"sitekey": sitekey
			}
	try:
		req = requests.post(HCAPTCHA_URL, data=data, timeout=5, verify=OUTBOUND_VERIFY)
		reply = req.json()
	except (requests.RequestException, ValueError) as e:
		print(f"[captcha] couldn't verify an answer with hCaptcha: {e!r}", file=sys.stderr, flush=True)
		return False
	verdict = reply.get("success") if isinstance(reply, dict) else None
	if not isinstance(verdict, bool):
		print(f"[captcha] hCaptcha's reply holds no verdict of true or false: {reply!r:.500}", file=sys.stderr, flush=True)
		return False
	return verdict
