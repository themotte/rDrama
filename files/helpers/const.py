from os import environ, listdir
import re
from copy import deepcopy
from json import loads
from files.__main__ import db_session
from files.classes.sub import Sub
from files.classes.marsey import Marsey
from flask import request

SITE = environ.get("DOMAIN", '').strip()
SITE_ID = environ.get("SITE_ID", '').strip()
SITE_TITLE = environ.get("SITE_TITLE", '').strip()
if "localhost" in SITE: SITE_FULL = 'http://' + SITE
else: SITE_FULL = 'https://' + SITE


CC = "COUNTRY CLUB"
CC_TITLE = CC.title()

NOTIFICATIONS_ID = 1
AUTOJANNY_ID = 2
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

IMGUR_KEY = environ.get("IMGUR_KEY").strip()
PUSHER_ID = environ.get("PUSHER_ID", "").strip()
PUSHER_KEY = environ.get("PUSHER_KEY", "").strip()
DEFAULT_COLOR = environ.get("DEFAULT_COLOR", "fff").strip()
COLORS = {'ff66ac','805ad5','62ca56','38a169','80ffff','2a96f3','eb4963','ff0000','f39731','30409f','3e98a7','e4432d','7b9ae4','ec72de','7f8fa6', 'f8db58','8cdbe6', DEFAULT_COLOR}

LOGGEDIN_ACTIVE_TIME = 15 * 60

AWARDS = {
	"lootbox": {
		"kind": "lootbox",
		"title": "Lootstocking",
		"description": "???",
		"icon": "fas fa-stocking",
		"color": "text-danger",
		"price": 1000
	},
	"shit": {
		"kind": "shit",
		"title": "Shit",
		"description": "Makes flies swarm the post.",
		"icon": "fas fa-poop",
		"color": "text-black-50",
		"price": 300
	},
	"fireflies": {
		"kind": "fireflies",
		"title": "Fireflies",
		"description": "Makes fireflies swarm the post.",
		"icon": "fas fa-sparkles",
		"color": "text-warning",
		"price": 300
	},
	"train": {
		"kind": "train",
		"title": "Train",
		"description": "Summons a train on the post.",
		"icon": "fas fa-train",
		"color": "text-pink",
		"price": 300
	},
	"scooter": {
		"kind": "scooter",
		"title": "Scooter",
		"description": "Summons a scooter on the post.",
		"icon": "fas fa-flag-usa",
		"color": "text-muted",
		"price": 300
	},
	"wholesome": {
		"kind": "wholesome",
		"title": "Wholesome",
		"description": "Summons a wholesome marsey on the post.",
		"icon": "fas fa-smile-beam",
		"color": "text-yellow",
		"price": 300
	},
	"tilt": {
		"kind": "tilt",
		"title": "Tilt",
		"description": "Tilts the post or comment",
		"icon": "fas fa-car-tilt",
		"color": "text-blue",
		"price": 300
	},
	"glowie": {
        "kind": "glowie",
        "title": "Glowie",
        "description": "Indicates that the recipient can be seen when driving. Just run them over.",
        "icon": "fas fa-user-secret",
        "color": "text-green",
        "price": 300
    },
	"pin": {
		"kind": "pin",
		"title": "1-Hour Pin",
		"description": "Pins the post/comment.",
		"icon": "fas fa-thumbtack fa-rotate--45",
		"color": "text-warning",
		"price": 1000
	},
	"unpin": {
		"kind": "unpin",
		"title": "1-Hour Unpin",
		"description": "Removes 1 hour from the pin duration of the post/comment.",
		"icon": "fas fa-thumbtack fa-rotate--45",
		"color": "text-black",
		"price": 1000
	},
	"ban": {
		"kind": "ban",
		"title": "1-Day Ban",
		"description": "Bans the recipient for a day.",
		"icon": "fas fa-gavel",
		"color": "text-danger",
		"price": 3000
	},
	"unban": {
		"kind": "unban",
		"title": "1-Day Unban",
		"description": "Removes 1 day from the ban duration of the recipient.",
		"icon": "fas fa-gavel",
		"color": "text-success",
		"price": 3500
	},
	"benefactor": {
		"kind": "benefactor",
		"title": "Benefactor",
		"description": "Grants one month of paypig status and 2500 marseybux to the recipient. Cannot be used on yourself.",
		"icon": "fas fa-gift",
		"color": "text-blue",
		"price": 4000
	},
	"grass": {
		"kind": "grass",
		"title": "Grass",
		"description": "Doesn't do anything",
		"icon": "fas fa-seedling",
		"color": "text-success",
		"price": 10000
	},
}

AWARDS2 = deepcopy(AWARDS)
for k, val in AWARDS.items():
	if val['description'] == '???': AWARDS2.pop(k)


AWARDS3 = {}
for k, val in AWARDS2.items():
	if val['price'] == 300: AWARDS3[k] = val

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

christian_emojis = (':#marseyjesus:',':#marseyimmaculate:',':#marseymothermary:',':#marseyfatherjoseph:',':#gigachadorthodox:',':#marseyorthodox:',':#marseyorthodoxpat:')

db = db_session()
marseys_const = [x[0] for x in db.query(Marsey.name).filter(Marsey.name!='chudsey').all()]
marseys_const2 = marseys_const + ['chudsey','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','0','1','2','3','4','5','6','7','8','9','exclamationpoint','period','questionmark']
db.close()

valid_username_chars = 'a-zA-Z0-9_\\-'
valid_username_regex = re.compile("^[a-zA-Z0-9_\\-]{3,25}$", flags=re.A)
mention_regex = re.compile('(^|\\s|<p>)@(([a-zA-Z0-9_\\-]){1,25})', flags=re.A)
mention_regex2 = re.compile('<p>@(([a-zA-Z0-9_\\-]){1,25})', flags=re.A)

valid_password_regex = re.compile("^.{8,100}$", flags=re.A)

marsey_regex = re.compile("[a-z0-9]{1,30}", flags=re.A)

tags_regex = re.compile("[a-z0-9: ]{1,200}", flags=re.A)

valid_sub_regex = re.compile("^[a-zA-Z0-9_\\-]{3,20}$", flags=re.A)

query_regex = re.compile("(\\w+):(\\S+)", flags=re.A)

title_regex = re.compile("[^\\w ]", flags=re.A)

based_regex = re.compile("based and (.{1,20}?)(-| )pilled", flags=re.I|re.A)

controversial_regex = re.compile('["> ](https:\\/\\/old\\.reddit\\.com/r/[a-zA-Z0-9_]{3,20}\\/comments\\/[\\w\\-.#&/=\\?@%+]{5,250})["< ]', flags=re.A)

fishylinks_regex = re.compile("https?://\\S+", flags=re.A)

spoiler_regex = re.compile('''\\|\\|(.+)\\|\\|''', flags=re.A)
reddit_regex = re.compile('(^|\\s|<p>)\\/?((r|u)\\/(\\w|-){3,25})(?![^<]*<\\/(code|pre|a)>)', flags=re.A)
sub_regex = re.compile('(^|\\s|<p>)\\/?(h\\/(\\w|-){3,25})', flags=re.A)

# Bytes that shouldn't be allowed in user-submitted text
# U+200E is LTR toggle,  U+200F is RTL toggle, U+200B and U+FEFF are Zero-Width Spaces,
# and U+1242A is a massive and terrifying cuneiform numeral
unwanted_bytes_regex = re.compile("\u200e|\u200f|\u200b|\ufeff|\U0001242a")

whitespace_regex = re.compile('\\s+')

strikethrough_regex = re.compile('''~{1,2}([^~]+)~{1,2}''', flags=re.A)

mute_regex = re.compile("/mute @([a-z0-9_\\-]{3,25}) ([0-9])+", flags=re.A)

emoji_regex = re.compile(f"[^a]>\\s*(:[!#@]{{0,3}}[{valid_username_chars}]+:\\s*)+<\\/", flags=re.A)
emoji_regex2 = re.compile(f"(?<!\"):([!#@{valid_username_chars}]{{1,31}}?):", flags=re.A)
emoji_regex3 = re.compile(f"(?<!\"):([!@{valid_username_chars}]{{1,31}}?):", flags=re.A)

snappy_url_regex = re.compile('<a href=\\"(https?:\\/\\/[a-z]{1,20}\\.[\\w:~,()\\-.#&\\/=?@%;+]{5,250})\\" rel=\\"nofollow noopener noreferrer\\" target=\\"_blank\\">([\\w:~,()\\-.#&\\/=?@%;+]{5,250})<\\/a>', flags=re.A)

# Technically this allows stuff that is not a valid email address, but realistically
# we care "does this email go to the correct person" rather than "is this email
# address syntactically valid", so if we care we should be sending a confirmation
# link, and otherwise should be pretty liberal in what we accept here.
email_regex = re.compile('[^@]+@[^@]+\\.[^@]+', flags=re.A)

utm_regex = re.compile('utm_[a-z]+=[a-z0-9_]+&', flags=re.A)
utm_regex2 = re.compile('[?&]utm_[a-z]+=[a-z0-9_]+', flags=re.A)

YOUTUBE_KEY = environ.get("YOUTUBE_KEY", "").strip()

proxies = {"http":"http://127.0.0.1:18080","https":"http://127.0.0.1:18080"}

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

youtube_regex = re.compile('(<p>[^<]*)(https:\\/\\/youtube\\.com\\/watch\\?v\\=([a-z0-9-_]{5,20})[\\w\\-.#&/=\\?@%+]*)', flags=re.I|re.A)

yt_id_regex = re.compile('[a-z0-9-_]{5,20}', flags=re.I|re.A)

image_regex = re.compile("(^|\\s)(https:\\/\\/[\\w\\-.#&/=\\?@%;+]{5,250}(\\.png|\\.jpg|\\.jpeg|\\.gif|\\.webp|maxwidth=9999|fidelity=high))($|\\s)", flags=re.I|re.A)

procoins_li = (0,2500,5000,10000,25000,50000,125000,250000)

linefeeds_regex = re.compile("([^\\n])\\n([^\\n])", flags=re.A)

def make_name(*args, **kwargs): return request.base_url
