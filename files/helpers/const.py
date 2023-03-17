import re
import sys
from copy import deepcopy
from enum import IntEnum
from os import environ
from typing import Final

from flask import request

SITE = environ.get("DOMAIN", '').strip()
SITE_ID = environ.get("SITE_ID", '').strip()
SITE_TITLE = environ.get("SITE_TITLE", '').strip()
SCHEME = environ.get('SCHEME', 'http' if 'localhost' in SITE else 'https')
SITE_FULL = SCHEME + '://' + SITE

class Service(IntEnum):
	THEMOTTE = 0
	CRON = 1
	CHAT = 2

	@classmethod
	def from_argv(cls):
		if "cron" in sys.argv:
			return cls.CRON
		if "load_chat" in sys.argv:
			return cls.CHAT
		return cls.THEMOTTE

CC = "COUNTRY CLUB"
CC_TITLE = CC.title()

NOTIFICATIONS_ID = 1
AUTOJANNY_ID = 2
MODMAIL_ID = 2
SNAPPY_ID = 3
LONGPOSTBOT_ID = 4
ZOZBOT_ID = 5
AUTOPOLLER_ID = 6
AUTOBETTER_ID = 7
AUTOCHOICE_ID = 8
BASEDBOT_ID = 0

GIFT_NOTIF_ID = 9
OWNER_ID = 9
BUG_THREAD = 0
WELCOME_MSG = f"Welcome to {SITE_TITLE}! Please read [the rules](/rules) first. Then [read some of our current conversations](/) and feel free to comment or post!\n\nWe encourage people to comment even if they aren't sure they fit in; as long as your comment follows [community rules](/rules), we are happy to have posters from all backgrounds, education levels, and specialties."
ROLES={}

LEADERBOARD_LIMIT: Final[int] = 25

THEMES = {"TheMotte", "dramblr", "reddit", "transparent", "win98", "dark", 
			"light", "coffee", "tron", "4chan", "midnight"}
SORTS_COMMON = {
	"top": 'fa-arrow-alt-circle-up', 
	"bottom": 'fa-arrow-alt-circle-down', 
	"new": 'fa-sparkles', 
	"old": 'fa-book', 
	"controversial": 'fa-bullhorn',
	"comments": 'fa-comments'
}
SORTS_POSTS = {
	"hot": "fa-fire",
	"bump": "fa-arrow-up"
}
SORTS_POSTS.update(SORTS_COMMON)
SORTS_COMMENTS = SORTS_COMMON

MAX_CONTENT_LENGTH = 16 * 1024 * 1024
SESSION_COOKIE_SAMESITE = "Lax"
PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 365
DEFAULT_THEME = "TheMotte"
FORCE_HTTPS = 1
PUSHER_ID = environ.get("PUSHER_ID", "").strip()
PUSHER_KEY = environ.get("PUSHER_KEY", "").strip()
DEFAULT_COLOR = environ.get("DEFAULT_COLOR", "fff").strip()
COLORS = {'ff66ac','805ad5','62ca56','38a169','80ffff','2a96f3','eb4963','ff0000','f39731','30409f','3e98a7','e4432d','7b9ae4','ec72de','7f8fa6', 'f8db58','8cdbe6', DEFAULT_COLOR}

SUBMISSION_FLAIR_LENGTH_MAXIMUM: Final[int] = 350
SUBMISSION_TITLE_LENGTH_MAXIMUM: Final[int] = 500
SUBMISSION_URL_LENGTH_MAXIMUM: Final[int] = 2048
SUBMISSION_BODY_LENGTH_MAXIMUM: Final[int] = 20000
COMMENT_BODY_LENGTH_MAXIMUM: Final[int] = 10000
MESSAGE_BODY_LENGTH_MAXIMUM: Final[int] = 10000
CSS_LENGTH_MAXIMUM: Final[int] = 4000

ERROR_MESSAGES = {
	400: "That request was bad and you should feel bad",
	401: "You need an account for this. Please make one!",
	403: "You don't have access to this page.",
	404: "That page doesn't exist. If you got here from a link on the website, please report this issue. Thanks!",
	405: "Something went wrong and it's probably my fault. If you can do it reliably, or it's causing problems for you, please report it!",
	409: "There's a conflict between what you're trying to do and what you or someone else has done and because of that you can't do what you're trying to do.",
	413: "Max file size is 8 MB",
	422: "Something is wrong about your request. If you keep getting this unexpectedly, please report it!",
	429: "Are you hammering the site? Stop that, yo.",
	500: "Something went wrong and it's probably my fault. If you can do it reliably, or it's causing problems for you, please report it!",
}

LOGGEDIN_ACTIVE_TIME = 15 * 60
RENDER_DEPTH_LIMIT = 9
'''
The maximum depth at which a comment tree is rendered
'''

WERKZEUG_ERROR_DESCRIPTIONS = {
	400: "The browser (or proxy) sent a request that this server could not understand.",
	401: "The server could not verify that you are authorized to access the URL requested. You either supplied the wrong credentials (e.g. a bad password), or your browser doesn't understand how to supply the credentials required.",
	403: "You don't have the permission to access the requested resource. It is either read-protected or not readable by the server.",
	404: "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
	405: "The method is not allowed for the requested URL.",
	409: "A conflict happened while processing the request. The resource might have been modified while the request was being processed.",
	413: "The data value transmitted exceeds the capacity limit.",
	415: "The server does not support the media type transmitted in the request.",
	422: "The request was well-formed but was unable to be followed due to semantic errors.",
	429: "This user has exceeded an allotted request count. Try again later.",
	500: "The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.",
}

IMAGE_FORMATS = ['png','gif','jpg','jpeg','webp']
IMAGE_URL_ENDINGS = IMAGE_FORMATS + ['.webp', '.jpg', '.png', '.gif', '.jpeg', '?maxwidth=9999', '&fidelity=high']
VIDEO_FORMATS = ['mp4','webm','mov','avi','mkv','flv','m4v','3gp']
AUDIO_FORMATS = ['mp3','wav','ogg','aac','m4a','flac']
NO_TITLE_EXTENSIONS = IMAGE_FORMATS + VIDEO_FORMATS + AUDIO_FORMATS

FEATURES = {
	"AWARDS": False,
	"EMOJI": False,
}

PERMS = {
	"DEBUG_LOGIN_TO_OTHERS": 3,
	'PERFORMANCE_KILL_PROCESS': 3,
	'PERFORMANCE_SCALE_UP_DOWN': 3,
	'PERFORMANCE_RELOAD': 3,
	'PERFORMANCE_STATS': 3,
	"POST_COMMENT_MODERATION": 2,
	"USER_SHADOWBAN": 2,
}

AWARDS = {}

if FEATURES['AWARDS']:
	AWARDS_ENABLED = deepcopy(AWARDS)
	for k, val in AWARDS.items():
		if val['description'] == '???': AWARDS_ENABLED.pop(k)

	AWARDS_JL2_PRINTABLE = {}
	for k, val in AWARDS_ENABLED.items():
		if val['price'] == 300: AWARDS_JL2_PRINTABLE[k] = val
else:
	AWARDS_ENABLED = {}
	AWARDS_JL2_PRINTABLE = {}


NOTIFIED_USERS = {
	# format: 'substring' ↦ User ID to notify
}

patron = 'Patron'

discounts = {
	69: 0.02,
	70: 0.04,
	71: 0.06,
	72: 0.08,
	73: 0.10,
}

CF_KEY = environ.get("CF_KEY", "").strip()
CF_ZONE = environ.get("CF_ZONE", "").strip()
CF_HEADERS = {"Authorization": f"Bearer {CF_KEY}", "Content-Type": "application/json"}

dues = int(environ.get("DUES").strip())

proxies = {}

approved_embed_hosts = [
	'rdrama.net',
	'pcmemes.net',
	'cringetopia.org',
	'devrama.xyz',
	'imgur.com',
	'ibb.co',
	'lain.la',
	'pngfind.com',
	'kym-cdn.com',
	'redd.it',
	'substack.com',
	'blogspot.com',
	'catbox.moe',
	'pinimg.com',
	'kindpng.com',
	'shopify.com',
	'discordapp.com',
	'discordapp.net',
	'twimg.com',
	'wikimedia.org',
	'wp.com',
	'wordpress.com',
	'seekpng.com',
	'dailymail.co.uk',
	'cdc.gov',
	'media-amazon.com',
	'ssl-images-amazon.com',
	'washingtonpost.com',
	'imgflip.com',
	'flickr.com',
	'9cache.com',
	'ytimg.com',
	'foxnews.com',
	'duckduckgo.com',
	'forbes.com',
	'gr-assets.com',
	'tenor.com',
	'giphy.com',
	'makeagif.com',
	'gfycat.com',
	'tumblr.com',
	'yarn.co',
	'gifer.com',
	'prnt.sc',
	'staticflickr.com',
	'kiwifarms.net',
	'amazonaws.com',
	'githubusercontent.com',
	'unilad.co.uk',
	'grrrgraphics.com',
	'redditmedia.com'
	]

hosts = "|".join(approved_embed_hosts).replace('.','\\.')
image_check_regex = re.compile(f'!\\[\\]\\(((?!(https:\\/\\/([a-z0-9-]+\\.)*({hosts})\\/|\\/)).*?)\\)', flags=re.A)
embed_fullmatch_regex = re.compile(f'https:\\/\\/([a-z0-9-]+\\.)*({hosts})\\/[\\w:~,()\\-.#&\\/=?@%;+]*', flags=re.A)
video_sub_regex = re.compile(f'(<p>[^<]*)(https:\\/\\/([a-z0-9-]+\\.)*({hosts})\\/[\\w:~,()\\-.#&\\/=?@%;+]*?\\.(mp4|webm|mov))', flags=re.A)

procoins_li = (0,2500,5000,10000,25000,50000,125000,250000)

from files.helpers.config.regex import *

def make_name(*args, **kwargs): return request.base_url
