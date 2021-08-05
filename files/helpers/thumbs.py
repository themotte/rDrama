from .get import *

def expand_url(post_url, fragment_url):

	# convert src into full url
	if fragment_url.startswith("https://"):
		return fragment_url
	elif fragment_url.startswith("http://"):
		return f"https://{fragment_url.split('http://')[1]}"
	elif fragment_url.startswith('//'):
		return f"https:{fragment_url}"
	elif fragment_url.startswith('/'):
		parsed_url = urlparse(post_url)
		return f"https://{parsed_url.netloc}{fragment_url}"
	else:
		return f"{post_url}{'/' if not post_url.endswith('/') else ''}{fragment_url}"

def thumbnail_thread(pid, debug=False):

	return True, "Success"