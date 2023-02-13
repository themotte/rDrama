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
	req = requests.post(HCAPTCHA_URL, data=data, timeout=5)
	return bool(req.json()["success"])
