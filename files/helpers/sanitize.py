import functools
import html
import re
import urllib.parse
from functools import partial
from typing import Optional

import bleach
from bleach.css_sanitizer import CSSSanitizer
from bleach.linkifier import LinkifyFilter, build_url_re
from bs4 import BeautifulSoup, NavigableString
from flask import abort, g
from mistletoe import HTMLRenderer, markdown

from files.classes.domains import BannedDomain
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


_TEXT_ONLY_SKIP = {"a", "code", "pre", "script", "style"}


def _on_text(soup, transform):
	'''Replaces each run of text in `soup` outside links and code with `transform` of it, escaped as HTML; parts that are web addresses are left alone.'''
	for node in list(soup.find_all(string=True)):
		if type(node) is not NavigableString or any(parent.name in _TEXT_ONLY_SKIP for parent in node.parents):
			continue
		escaped = html.escape(str(node), quote=False)
		changed = "".join(part if url_re.fullmatch(part) else transform(part) for part in _split_addresses(escaped))
		if changed != escaped:
			node.replace_with(*BeautifulSoup(changed, "html.parser").contents)


def _split_addresses(text: str) -> list[str]:
	'''`text` cut into web addresses and the rest, in order.'''
	parts, start = [], 0
	for match in url_re.finditer(text):
		parts += [text[start:match.start()], match.group(0)]
		start = match.end()
	return [part for part in parts + [text[start:]] if part]


_strikethrough_text_regex = re.compile(r'(~{1,2})([^~]+?)\1', flags=re.A)
_reddit_text_regex = re.compile(r'(^|\s)/?((?:r|u)/[\w-]{3,25})(?![\w-])', flags=re.A)
_hole_text_regex = re.compile(r'(^|\s)/?(h/[\w-]{3,25})(?![\w-])', flags=re.A)
_mention_text_regex = re.compile(r'(^|\s)@([a-zA-Z0-9_\-]{1,25})(?![a-zA-Z0-9_\-])', flags=re.A)


def _formatting(text: str) -> str:
	text = _strikethrough_text_regex.sub(r'<del>\2</del>', text)
	return spoiler_regex.sub(r'<spoiler>\1</spoiler>', text)


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

_ADDRESS_REWRITES = [
	*((old, "://old.reddit.com") for old in ("://reddit.com", "://new.reddit.com", "://www.reddit.com", "://redd.it", "://libredd.it", "://teddit.net")),
	("nitter.net", "twitter.com"), ("old.reddit.com/gallery", "reddit.com/gallery"),
	("https://youtu.be/", "https://youtube.com/watch?v="), ("https://music.youtube.com/watch?v=", "https://youtube.com/watch?v="),
	("https://streamable.com/", "https://streamable.com/e/"), ("https://youtube.com/shorts/", "https://youtube.com/watch?v="),
	("https://mobile.twitter", "https://twitter"), ("https://m.facebook", "https://facebook"), ("m.wikipedia.org", "wikipedia.org"),
	("https://m.youtube", "https://youtube"), ("https://www.youtube", "https://youtube"), ("https://www.twitter", "https://twitter"),
	("https://www.instagram", "https://instagram"), ("https://www.tiktok", "https://tiktok"),
]


def _rewritten_address(address: str) -> str:
	'''`address` with the site rewrites applied, a YouTube video's start time taken as "&t=", and tracking parameters removed.'''
	for old, new in _ADDRESS_REWRITES:
		address = address.replace(old, new)
	if address.startswith("https://youtube.com/watch?v="): address = address.replace("?t=", "&t=")
	return utm_regex2.sub('', utm_regex.sub('', address))


class _Renderer(HTMLRenderer):
	_links_open = 0

	def render_link(self, token) -> str:
		self._links_open += 1
		try: return super().render_link(token)
		finally: self._links_open -= 1

	def render_image(self, token) -> str:
		'''Images aren't shown inline: each becomes a link to it, labelled with its text or else its address; inside a link, just that label.'''
		label = self.render_inner(token) or html.escape(token.src)
		return label if self._links_open else f'<a href="{self.escape_url(token.src)}">{label}</a>'


def sanitize(sanitized):
	# remove left-to-right mark; remove zero width space; remove zero width no-break space; remove Cuneiform Numeric Sign Eight;
	sanitized = unwanted_bytes_regex.sub('', sanitized)

	# transform markdown into html
	sanitized = markdown(sanitized, renderer=_Renderer)

	# The site's conventions apply to runs of text, never inside code, links, addresses or markup
	soup = BeautifulSoup(sanitized, 'html.parser')
	_on_text(soup, _formatting)

	mentioned = set()
	_on_text(soup, lambda text: mentioned.update(m.group(2).lower() for m in _mention_text_regex.finditer(text)) or text)
	users = {}
	for u in get_users(mentioned, graceful=True):
		if not u: continue
		users[u.username.lower()] = users[u.original_username.lower()] = u
	if len(set(users.values())) > MENTION_LIMIT:
		abort(400, f'Mentioned {len(set(users.values()))} users but limit is {MENTION_LIMIT}')

	def _mention(m):
		u = users.get(m.group(2).lower())
		if not u or (g.v and g.v.any_block_exists(u) and g.v.admin_level < 2): return m.group(0)
		return f'{m.group(1)}<a href="/id/{u.id}">@{u.username}</a>'

	def _links(text: str) -> str:
		text = _reddit_text_regex.sub(r'\1<a href="https://old.reddit.com/\2" rel="nofollow noopener noreferrer">/\2</a>', text)
		text = _hole_text_regex.sub(r'\1<a href="/\2">/\2</a>', text)
		return _mention_text_regex.sub(_mention, text)

	_on_text(soup, _links)

	for tag in soup.find_all("a"):
		if tag.get("href") and fishylinks_regex.fullmatch(str(tag.string)):
			tag.string = tag["href"]

	sanitized = str(soup)

	sanitized = bleach.Cleaner(tags=allowed_tags,
								attributes=allowed_attributes,
								protocols=['http', 'https'],
								css_sanitizer=css_sanitizer,
								filters=[partial(LinkifyFilter, skip_tags=["pre", "code"], parse_email=False, callbacks=[callback], url_re=url_re)],
								strip=True,
								).clean(sanitized)

	soup = BeautifulSoup(sanitized, 'html.parser')

	links = soup.find_all("a")
	for link in links:
		href = link.get("href")
		if not href: continue
		shown = link.string in (href, href.split("://", 1)[-1])
		link["href"] = _rewritten_address(href)
		if shown: link.string = link["href"] if link.string == href else link["href"].split("://", 1)[-1]

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
	return str(soup)


def filter_emojis_only(title):
	title = unwanted_bytes_regex.sub('', title)
	title = whitespace_regex.sub(' ', title)
	title = html.escape(title, quote=True)

	return strikethrough_regex.sub(r'<del>\1</del>', title)

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
