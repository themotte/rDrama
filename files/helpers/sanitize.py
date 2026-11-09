import functools
import html
import re
import urllib.parse
from functools import partial
from typing import Optional

import bleach
from bleach.css_sanitizer import CSSSanitizer
from bleach.linkifier import LinkifyFilter, build_url_re
from bs4 import BeautifulSoup
from flask import abort, g
from mistletoe import markdown

from files.classes.domains import BannedDomain
from files.helpers.config.const import image_check_regex
from files.helpers.config.environment import MENTION_LIMIT, SITE_FULL
from files.helpers.config.regex import *
from files.helpers.get import get_users

TLDS = ('ac','ad','ae','aero','af','ag','ai','al','am','an','ao','aq','ar',
	'arpa','as','asia','at','au','aw','ax','az','ba','bb','bd','be','bf','bg',
	'bh','bi','biz','bj','bm','bn','bo','br','bs','bt','bv','bw','by','bz',
	'ca','cafe','cat','cc','cd','cf','cg','ch','ci','ck','cl','club','cm',
	'cn','co','com','coop','cr','cu','cv','cx','cy','cz','de','dj','dk','dm',
	'do','dz','ec','edu','ee','eg','er','es','et','eu','fi','fj','fk','fm',
	'fo','fr','ga','gb','gd','ge','gf','gg','gh','gi','gl','gm','gn','gov',
	'gp','gq','gr','gs','gt','gu','gw','gy','hk','hm','hn','hr','ht','hu',
	'id','ie','il','im','in','info','int','io','iq','ir','is','it','je','jm',
	'jo','jobs','jp','ke','kg','kh','ki','km','kn','kp','kr','kw','ky','kz',
	'la','lb','lc','li','lk','lr','ls','lt','lu','lv','ly','ma','mc','md','me',
	'mg','mh','mil','mk','ml','mm','mn','mo','mobi','mp','mq','mr','ms','mt',
	'mu','museum','mv','mw','mx','my','mz','na','name','nc','ne','net','nf',
	'ng','ni','nl','no','np','nr','nu','nz','om','org','pa','pe','pf','pg',
	'ph','pk','pl','pm','pn','post','pr','pro','ps','pt','pw','py','qa','re',
	'ro','rs','ru','rw','sa','sb','sc','sd','se','sg','sh','si','sj','sk',
	'sl','sm','sn','so','social','sr','ss','st','su','sv','sx','sy','sz',
	'tc','td','tel','tf','tg','th','tj','tk','tl','tm','tn','to','tp','tr',
	'travel','tt','tv','tw','tz','ua','ug','uk','us','uy','uz','va','vc','ve',
	'vg','vi','vn','vu','wf','win','ws','xn','xxx','xyz','ye','yt','yu','za',
	'zm','zw', 'moe')

allowed_tags = ('b','blockquote','br','code','del','em','h1','h2','h3','h4',
		'h5','h6','hr','i','li','ol','p','pre','strong','sub','sup','table',
		'tbody','th','thead','td','tr','ul','a','span','ruby','rp','rt',
		'spoiler',)

def allowed_attributes(tag, name, value):
	if name == 'style': return True

	if tag == 'a':
		if name == 'href': return True
		if name == 'rel' and value == 'nofollow noopener noreferrer': return True
		if name == 'target' and value == '_blank': return True
		return False

	if tag == 'p':
		return False

	if tag == 'span':
		if name == 'data-bs-toggle' and value == 'tooltip': return True
		if name == 'title': return True
		if name == 'alt': return True
		return False


_tag_or_strikethrough_regex = re.compile(r'(<[^>]+>)|(~{1,2})([^~]+?)\2', flags=re.A)

def _strikethrough_replace(m):
	if m.group(1):  # matched an HTML tag — return unchanged
		return m.group(1)
	return '<del>' + m.group(3) + '</del>'

def _apply_strikethrough(text):
	"""Apply strikethrough formatting only to text outside HTML tags."""
	return _tag_or_strikethrough_regex.sub(_strikethrough_replace, text)

url_re = build_url_re(tlds=TLDS, protocols=['http', 'https'])

css_sanitizer = CSSSanitizer(allowed_css_properties=['color', 'background-color', 'font-weight', 'text-align'])

def callback(attrs, new=False):
	href = attrs.get((None, "href"), None)
	if href == None:
		return attrs

	if not href.startswith('/') and not href.startswith(f'{SITE_FULL}/'):
		attrs[(None, "target")] = "_blank"
		attrs[(None, "rel")] = "nofollow noopener noreferrer"	

	return attrs


REMOVED_CHARACTERS = ['\u200e', '\u200b', '\ufeff']
"""
Characters which are removed from content
"""

def sanitize_raw(sanitized:Optional[str], allow_newlines:bool, length_limit:Optional[int]) -> str:
	if not sanitized: return ""
	for char in REMOVED_CHARACTERS:
		sanitized = sanitized.replace(char, '')
	if allow_newlines:
		sanitized = sanitized.replace("\r\n", "\n")
	else:
		sanitized = sanitized.replace("\r","").replace("\n", "")
	sanitized = sanitized.strip()
	if length_limit is not None:
		sanitized = sanitized[:length_limit]
	return sanitized

def sanitize(sanitized, alert=False):
	# if image url in whitelist, do nothing
	# eg. ![](https://wikipedia.org/someimage.jpg) turns into ![](https://wikipedia.org/someimage.jpg)
	# but if not, then extract url
	# eg ![](https://example.org/someimage.jpg) turns into https://example.org/someimage.jpg
	sanitized = image_check_regex.sub(r'\1', sanitized)

	# transform markdown into html
	sanitized = markdown(sanitized)

	# turn ~something~ or ~~something~~  into <del>something</del>
	# skip text inside HTML tags so tildes in URLs aren't mangled (fixes #737)
	sanitized = _apply_strikethrough(sanitized)

	# remove left-to-right mark; remove zero width space; remove zero width no-break space; remove Cuneiform Numeric Sign Eight;
	sanitized = unwanted_bytes_regex.sub('', sanitized)

	if alert:
		matches = { g.group(1):g for g in mention_regex2.finditer(sanitized) if g }
		users = get_users(matches.keys(),graceful=True)

		captured = []
		for u in users:
			if u:
				i = matches.get(u.username) or matches.get(u.original_username)
				if i.group(0) not in captured:
					captured.append(i.group(0))
					sanitized = sanitized.replace(i.group(0), f'''<p><a href="/id/{u.id}"><img loading="lazy" src="/pp/{u.id}">@{u.username}</a>''')
	else:
		sanitized = reddit_regex.sub(r'\1<a href="https://old.reddit.com/\2" rel="nofollow noopener noreferrer">/\2</a>', sanitized)
		sanitized = sub_regex.sub(r'\1<a href="/\2">/\2</a>', sanitized)

		matches = [ m for m in mention_regex.finditer(sanitized) if m ]
		names = set(m.group(2) for m in matches)
		users = get_users(names,graceful=True)

		if len(users) > MENTION_LIMIT:
			abort(400, f'Mentioned {len(users)} users but limit is {MENTION_LIMIT}')

		for u in users:
			if not u: continue
			mention_is_u = lambda m: m.group(2).lower() in (u.username.lower(), u.original_username.lower())
			for i in filter(mention_is_u, matches):
				if not (g.v and g.v.any_block_exists(u)) or g.v.admin_level >= 2:
					sanitized = sanitized.replace(i.group(0), f'''{i.group(1)}<a href="/id/{u.id}"><img loading="lazy" src="/pp/{u.id}">@{u.username}</a>''', 1)

	soup = BeautifulSoup(sanitized, 'lxml')

	for tag in soup.find_all("a"):
		if tag.get("href") and fishylinks_regex.fullmatch(str(tag.string)):
			tag.string = tag["href"]


	sanitized = str(soup)

	sanitized = spoiler_regex.sub(r'<spoiler>\1</spoiler>', sanitized)

	for rd in ["://reddit.com", "://new.reddit.com", "://www.reddit.com", "://redd.it", "://libredd.it", "://teddit.net"]:
		sanitized = sanitized.replace(rd, "://old.reddit.com")

	sanitized = sanitized.replace("nitter.net", "twitter.com").replace("old.reddit.com/gallery", "reddit.com/gallery").replace("https://youtu.be/", "https://youtube.com/watch?v=").replace("https://music.youtube.com/watch?v=", "https://youtube.com/watch?v=").replace("https://streamable.com/", "https://streamable.com/e/").replace("https://youtube.com/shorts/", "https://youtube.com/watch?v=").replace("https://mobile.twitter", "https://twitter").replace("https://m.facebook", "https://facebook").replace("m.wikipedia.org", "wikipedia.org").replace("https://m.youtube", "https://youtube").replace("https://www.youtube", "https://youtube").replace("https://www.twitter", "https://twitter").replace("https://www.instagram", "https://instagram").replace("https://www.tiktok", "https://tiktok")


	if "https://youtube.com/watch?v=" in sanitized: sanitized = sanitized.replace("?t=", "&t=")

	sanitized = sanitized.replace('&amp;','&')
	sanitized = utm_regex.sub('', sanitized)
	sanitized = utm_regex2.sub('', sanitized)
	sanitized = sanitized.replace('<html><body>','').replace('</body></html>','')

	sanitized = bleach.Cleaner(tags=allowed_tags,
								attributes=allowed_attributes,
								protocols=['http', 'https'],
								css_sanitizer=css_sanitizer,
								filters=[partial(LinkifyFilter, skip_tags=["pre"], parse_email=False, callbacks=[callback], url_re=url_re)],
								strip=True,
								).clean(sanitized)

	soup = BeautifulSoup(sanitized, 'lxml')

	links = soup.find_all("a")

	domain_list = set()

	for link in links:

		href = link.get("href")
		if not href: continue

		url = urllib.parse.urlparse(href)
		domain = url.netloc
		url_path = url.path
		domain_list.add(domain+url_path)

		parts = domain.split(".")
		for i in range(len(parts)):
			new_domain = parts[i]
			for j in range(i + 1, len(parts)):
				new_domain += "." + parts[j]
				domain_list.add(new_domain)

	bans = g.db.query(BannedDomain.domain).filter(BannedDomain.domain.in_(list(domain_list))).all()
	if bans: abort(403, description=f"Remove the banned domains {bans} and try again!")
	return sanitized


def filter_emojis_only(title, graceful=False):
	title = unwanted_bytes_regex.sub('', title)
	title = whitespace_regex.sub(' ', title)
	title = html.escape(title, quote=True)

	title = strikethrough_regex.sub(r'<del>\1</del>', title)

	if len(title) > 1500 and not graceful: abort(400)
	else: return title

def validate_css(css:str) -> tuple[bool, str]:
	'''
	Validates that the provided CSS is allowed. It looks somewhat ugly but
	this prevents users from XSSing themselves (not really too much of a 
	practical concern) or causing styling issues with the rest of the page.
	'''
	if '</style' in css.lower(): return False, "Invalid CSS"
	if '@import' in css.lower(): return False, "@import statements are not allowed"
	if css_url_regex.search(css): return False, "External URL imports are not allowed"
	if 'image-set(' in css.lower(): return False, "External URL imports are not allowed"
	return True, ""
