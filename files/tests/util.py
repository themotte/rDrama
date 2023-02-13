
from bs4 import BeautifulSoup
import functools
import json
import random
import re
import string

def formkey_from(text):
    soup = BeautifulSoup(text, 'html.parser')
    formkey = next(tag for tag in soup.find_all("input") if tag.get("name") == "formkey").get("value")
    return formkey

# not cryptographically secure, deal with it
def generate_text():
    return ''.join(random.choices(string.ascii_lowercase, k=40))

# Annotation to put around tests that don't care about rate limits
def no_rate_limit(test_function):
	@functools.wraps(test_function)
	def wrapped(*args, **kwargs):
		from files.__main__ import app, limiter
		was_enabled = limiter.enabled
		app.config['RATE_LIMITER_ENABLED'] = False
		limiter.enabled = False
		try:
			result = test_function(*args, **kwargs)
			app.config['RATE_LIMITER_ENABLED'] = was_enabled
			limiter.enabled = was_enabled
			return result
		except Exception as e:
			app.config['RATE_LIMITER_ENABLED'] = was_enabled
			limiter.enabled = was_enabled
			raise e
	return wrapped

# this is meant to be a utility class that stores post and comment references so you can use them in other calls
# it's pretty barebones and will probably be fleshed out
class ItemData:
    id = None
    id_full = None
    url = None

    @staticmethod
    def from_html(text):
        soup = BeautifulSoup(text, 'html.parser')
        url = soup.find("meta", property="og:url")["content"]

        match = re.search(r'/post/(\d+)/', url)
        if match is None:
            return None
        
        result = ItemData()
        result.id = match.group(1)  	# this really should get yanked out of the JS, not the URL
        result.id_full = f"t2_{result.id}"
        result.url = url
        return result

    @staticmethod
    def from_json(text):
        data = json.loads(text)

        soup = BeautifulSoup(data["comment"], 'html.parser')
        divid = soup.find("div")["id"]

        match = re.search(r'comment-(\d+)', divid)
        if match is None:
            return None
        
        result = ItemData()
        result.id = match.group(1)  	# this really should get yanked out of the JS, not the HTML
        result.id_full = f"t3_{result.id}"
        result.url = f"/comment/{result.id}"
        return result
