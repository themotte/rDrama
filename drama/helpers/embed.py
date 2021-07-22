import re
from urllib.parse import *
import requests
from os import environ
from drama.__main__ import app

youtube_regex = re.compile("^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|shorts\/|\&v=)([^#\&\?]*).*")

drama_regex = re.compile("^.*rdrama.net/post/+\w+/(\w+)(/\w+/(\w+))?")

twitter_regex=re.compile("/status/(\d+)")

FACEBOOK_TOKEN=environ.get("FACEBOOK_TOKEN","").strip()



def youtube_embed(url):

	try:
		yt_id = re.match(youtube_regex, url).group(2)
	except AttributeError:
		return "error"

	if not yt_id or len(yt_id) != 11:
		return "error"

	x = urlparse(url)
	params = parse_qs(x.query)
	t = params.get('t', params.get('start', [0]))[0]
	if t:
		return f"https://youtube.com/embed/{yt_id}?start={t}"
	else:
		return f"https://youtube.com/embed/{yt_id}"


def drama_embed(url):

	matches = re.match(drama_regex, url)

	post_id = matches.group(1)
	comment_id = matches.group(3)

	if comment_id:
		return f"https://{app.config['SERVER_NAME']}/embed/comment/{comment_id}"
	else:
		return f"https://{app.config['SERVER_NAME']}/embed/post/{post_id}"


def bitchute_embed(url):

	return url.replace("/video/", "/embed/")

def twitter_embed(url):


	oembed_url=f"https://publish.twitter.com/oembed"
	params={
		"url":url,
		"omit_script":"t"
		}
	x=requests.get(oembed_url, params=params)

	return x.json()["html"]

def instagram_embed(url):

	oembed_url=f"https://graph.facebook.com/v9.0/instagram_oembed"
	params={
		"url":url,
		"access_token":FACEBOOK_TOKEN,
		"omitscript":'true'
	}

	headers={
		"User-Agent":"Instagram embedder for Drama"
	}

	x=requests.get(oembed_url, params=params, headers=headers)

	return x.json()["html"]