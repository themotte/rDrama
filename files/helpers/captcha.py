import sys
from typing import Final
import requests

HCAPTCHA_URL: Final[str] = "https://hcaptcha.com/siteverify"

def validate_captcha(secret:str, sitekey: str, token: str):
	if not sitekey: return True
	if not token: return False
	data = {"secret": secret,
			"response": token,
			"sitekey": sitekey
			}
	try:
		req = requests.post(HCAPTCHA_URL, data=data, timeout=5)
		return bool(req.json()["success"])
	except (requests.RequestException, ValueError, KeyError) as e:
		print(f"[captcha] couldn't verify an answer with hCaptcha: {e!r}", file=sys.stderr, flush=True)
		return False
