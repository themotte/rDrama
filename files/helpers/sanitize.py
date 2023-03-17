import functools
import html
import random
import re
from functools import partial
from os import path

import bleach
import gevent
from bleach.linkifier import LinkifyFilter, build_url_re
from bs4 import BeautifulSoup
from mistletoe import markdown

from files.helpers.const import image_check_regex, embed_fullmatch_regex, video_sub_regex
from files.helpers.content import canonicalize_url
from files.helpers.get import *
from files.helpers.regex import *
from files.__main__ import app # violates isort, but crashes otherwise

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

if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
	allowed_tags += ('img', 'lite-youtube', 'video', 'source',)


def allowed_attributes(tag, name, value):
	if name == 'style': return True

	if tag == 'a':
		if name == 'href': return True
		if name == 'rel' and value == 'nofollow noopener noreferrer': return True
		if name == 'target' and value == '_blank': return True
		return False

	if tag == 'img':
		if name in ['src','data-src']:
			if value.startswith('/') or value.startswith(f'{SITE_FULL}/') or embed_fullmatch_regex.fullmatch(value): return True
			else: return False

		if name == 'loading' and value == 'lazy': return True
		if name == 'referrpolicy' and value == 'no-referrer': return True
		if name == 'data-bs-toggle' and value == 'tooltip': return True
		if name in ['alt','title','g','b','pat']: return True
		if name == 'class' and value == 'pat-hand': return True
		return False

	if tag == 'lite-youtube':
		if name == 'params' and value.startswith('autoplay=1&modestbranding=1'): return True
		if name == 'videoid': return True
		return False

	if tag == 'video':
		if name == 'controls' and value == '': return True
		if name == 'preload' and value == 'none': return True
		return False

	if tag == 'source':
		if name == 'src' and embed_fullmatch_regex.fullmatch(value): return True
		return False

	if tag == 'p':
		if name == 'class' and value == 'mb-0': return True
		return False

	if tag == 'span':
		if name == 'class' and value in ['pat-container', 'pat-hand']: return True
		if name == 'data-bs-toggle' and value == 'tooltip': return True
		if name == 'title': return True
		if name == 'alt': return True
		return False


url_re = build_url_re(tlds=TLDS, protocols=['http', 'https'])

def callback(attrs, new=False):
	href = attrs.get((None, "href"), None)
	if href == None:
		return attrs

	if not href.startswith('/') and not href.startswith(f'{SITE_FULL}/'):
		attrs[(None, "target")] = "_blank"
		attrs[(None, "rel")] = "nofollow noopener noreferrer"	

	return attrs


def render_emoji(html, regexp, edit, marseys_used=set(), b=False):
	emojis = list(regexp.finditer(html))
	captured = set()

	for i in emojis:
		if i.group(0) in captured: continue
		captured.add(i.group(0))

		emoji = i.group(1).lower()
		attrs = ''
		if b: attrs += ' b'
		if not edit and len(emojis) <= 20 and random.random() < 0.0025 and ('marsey' in emoji or emoji in marseys_const2): attrs += ' g'

		old = emoji
		emoji = emoji.replace('!','').replace('#','')
		if emoji == 'marseyrandom': emoji = random.choice(marseys_const2)

		emoji_partial_pat = '<img loading="lazy" alt=":{0}:" src="{1}"{2}>'
		emoji_partial = '<img loading="lazy" data-bs-toggle="tooltip" alt=":{0}:" title=":{0}:" src="{1}"{2}>'
		emoji_html = None

		if emoji.endswith('pat'):
			if path.isfile(f"files/assets/images/emojis/{emoji.replace('pat','')}.webp"):
				attrs += ' pat'
				emoji_html = f'<span class="pat-container" data-bs-toggle="tooltip" alt=":{old}:" title=":{old}:"><img src="/assets/images/hand.webp" class="pat-hand">{emoji_partial_pat.format(old, f"/e/{emoji[:-3]}.webp", attrs)}</span>'
			elif emoji.startswith('@'):
				if u := get_user(emoji[1:-3], graceful=True):
					attrs += ' pat'
					emoji_html = f'<span class="pat-container" data-bs-toggle="tooltip" alt=":{old}:" title=":{old}:"><img src="/assets/images/hand.webp" class="pat-hand">{emoji_partial_pat.format(old, f"/pp/{u.id}", attrs)}</span>'
		elif path.isfile(f'files/assets/images/emojis/{emoji}.webp'):
			emoji_html = emoji_partial.format(old, f'/e/{emoji}.webp', attrs)


		if emoji_html:
			html = re.sub(f'(?<!"){i.group(0)}', emoji_html, html)
	return html


def with_gevent_timeout(timeout: int):
	'''
	Use gevent to raise an exception if the function executes for longer than timeout seconds
	Using gevent instead of a signal based approach allows for proper async and avoids some
	worker crashes
	'''
	def inner(func):
		@functools.wraps(func)
		def wrapped(*args, **kwargs):
			return gevent.with_timeout(timeout, func, *args, **kwargs)
		return wrapped
	return inner

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

@with_gevent_timeout(2)
def sanitize(sanitized, alert=False, comment=False, edit=False):
	# double newlines, eg. hello\nworld becomes hello\n\nworld, which later becomes <p>hello</p><p>world</p>
	sanitized = linefeeds_regex.sub(r'\1\n\n\2', sanitized)

	if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
		# turn eg. https://wikipedia.org/someimage.jpg into ![](https://wikipedia.org/someimage.jpg)
		sanitized = image_regex.sub(r'\1![](\2)\4', sanitized)

	# if image url in whitelist, do nothing
	# eg. ![](https://wikipedia.org/someimage.jpg) turns into ![](https://wikipedia.org/someimage.jpg)
	# but if not, then extract url
	# eg ![](https://example.org/someimage.jpg) turns into https://example.org/someimage.jpg
	sanitized = image_check_regex.sub(r'\1', sanitized)

	# transform markdown into html
	sanitized = markdown(sanitized)

	# turn ~something~ or ~~something~~  into <del>something</del>
	sanitized = strikethrough_regex.sub(r'<del>\1</del>', sanitized)

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

		if len(users) > app.config['MENTION_LIMIT']:
			abort(400, f'Mentioned {len(users)} users but limit is {app.config["MENTION_LIMIT"]}')

		for u in users:
			if not u: continue
			m = [ m for m in matches if u.username == m.group(2) or u.original_username == m.group(2) ]
			for i in m:
				if not (g.v and g.v.any_block_exists(u)) or g.v.admin_level > 1:
					sanitized = sanitized.replace(i.group(0), f'''{i.group(1)}<a href="/id/{u.id}"><img loading="lazy" src="/pp/{u.id}">@{u.username}</a>''', 1)

	soup = BeautifulSoup(sanitized, 'lxml')

	if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
		for tag in soup.find_all("img"):
			if tag.get("src") and not tag["src"].startswith('/pp/'):
				tag["loading"] = "lazy"
				tag["data-src"] = tag["src"]
				tag["src"] = "/assets/images/loading.webp"
				tag['alt'] = f'![]({tag["data-src"]})'
				tag['referrerpolicy'] = "no-referrer"

	for tag in soup.find_all("a"):
		if tag.get("href") and fishylinks_regex.fullmatch(str(tag.string)):
			tag.string = tag["href"]


	sanitized = str(soup)

	sanitized = spoiler_regex.sub(r'<spoiler>\1</spoiler>', sanitized)

	marseys_used = set()

	# emojis = list(emoji_regex.finditer(sanitized))
	# if len(emojis) > 20: edit = True

	# captured = []
	# for i in emojis:
	# 	if i.group(0) in captured: continue
	# 	captured.append(i.group(0))

	# 	old = i.group(0)
	# 	if 'marseylong1' in old or 'marseylong2' in old or 'marseyllama1' in old or 'marseyllama2' in old: new = old.lower().replace(">", " class='mb-0'>")
	# 	else: new = old.lower()

	# 	new = render_emoji(new, emoji_regex2, edit, marseys_used, True)

	# 	sanitized = sanitized.replace(old, new)

	# emojis = list(emoji_regex2.finditer(sanitized))
	# if len(emojis) > 20: edit = True

	# sanitized = render_emoji(sanitized, emoji_regex2, edit, marseys_used)

	for rd in ["://reddit.com", "://new.reddit.com", "://www.reddit.com", "://redd.it", "://libredd.it", "://teddit.net"]:
		sanitized = sanitized.replace(rd, "://old.reddit.com")

	sanitized = sanitized.replace("nitter.net", "twitter.com").replace("old.reddit.com/gallery", "reddit.com/gallery").replace("https://youtu.be/", "https://youtube.com/watch?v=").replace("https://music.youtube.com/watch?v=", "https://youtube.com/watch?v=").replace("https://streamable.com/", "https://streamable.com/e/").replace("https://youtube.com/shorts/", "https://youtube.com/watch?v=").replace("https://mobile.twitter", "https://twitter").replace("https://m.facebook", "https://facebook").replace("m.wikipedia.org", "wikipedia.org").replace("https://m.youtube", "https://youtube").replace("https://www.youtube", "https://youtube").replace("https://www.twitter", "https://twitter").replace("https://www.instagram", "https://instagram").replace("https://www.tiktok", "https://tiktok")


	if "https://youtube.com/watch?v=" in sanitized: sanitized = sanitized.replace("?t=", "&t=")

	if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
		captured = []
		for i in youtube_regex.finditer(sanitized):
			if i.group(0) in captured: continue
			captured.append(i.group(0))

			params = parse_qs(urlparse(i.group(2).replace('&amp;','&')).query)
			t = params.get('t', params.get('start', [0]))[0]
			if isinstance(t, str): t = t.replace('s','')

			htmlsource = f'{i.group(1)}<lite-youtube videoid="{i.group(3)}" params="autoplay=1&modestbranding=1'
			if t: htmlsource += f'&start={t}'
			htmlsource += '"></lite-youtube>'

			sanitized = sanitized.replace(i.group(0), htmlsource)

	if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
		sanitized = video_sub_regex.sub(r'\1<video controls preload="none"><source src="\2"></video>', sanitized)

	if comment:
		for marsey in g.db.query(Marsey).filter(Marsey.name.in_(marseys_used)).all():
			marsey.count += 1
			g.db.add(marsey)

	sanitized = sanitized.replace('&amp;','&')
	sanitized = utm_regex.sub('', sanitized)
	sanitized = utm_regex2.sub('', sanitized)
	sanitized = sanitized.replace('<html><body>','').replace('</body></html>','')

	sanitized = bleach.Cleaner(tags=allowed_tags,
								attributes=allowed_attributes,
								protocols=['http', 'https'],
								styles=['color', 'background-color', 'font-weight', 'text-align'],
								filters=[partial(LinkifyFilter, skip_tags=["pre"], parse_email=False, callbacks=[callback], url_re=url_re)],
								strip=True,
								).clean(sanitized)

	soup = BeautifulSoup(sanitized, 'lxml')

	links = soup.find_all("a")

	domain_list = set()

	for link in links:

		href = link.get("href")
		if not href: continue

		url = urlparse(href)
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


def allowed_attributes_emojis(tag, name, value):
	if tag == 'img':
		if name == 'loading' and value == 'lazy': return True
		if name == 'data-bs-toggle' and value == 'tooltip': return True
		if name in ['src','alt','title','g']: return True
	return False


@with_gevent_timeout(1)
def filter_emojis_only(title, edit=False, graceful=False):
	title = unwanted_bytes_regex.sub('', title)
	title = whitespace_regex.sub(' ', title)
	title = html.escape(title, quote=True)

	# title = render_emoji(title, emoji_regex3, edit)

	title = strikethrough_regex.sub(r'<del>\1</del>', title)

	sanitized = bleach.clean(title, tags=['img','del'], attributes=allowed_attributes_emojis, protocols=['http','https'])

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
	return True, ""


def sanitize_url(url:Optional[str]) -> Optional[str]:
	if not url: return None
	url = canonicalize_url(url)
	parsed_url = urlparse(url)

	domain = parsed_url.netloc
	if domain in ('old.reddit.com','twitter.com','instagram.com','tiktok.com'):
		new_url = ParseResult(scheme="https",
				netloc=parsed_url.netloc,
				path=parsed_url.path,
				params=parsed_url.params,
				query=None,
				fragment=parsed_url.fragment)
	else:
		qd = parse_qs(parsed_url.query)
		filtered = {k: val for k, val in qd.items() if not k.startswith('utm_') and not k.startswith('ref_')}

		new_url = ParseResult(scheme="https",
							netloc=parsed_url.netloc,
							path=parsed_url.path,
							params=parsed_url.params,
							query=urlencode(filtered, doseq=True),
							fragment=parsed_url.fragment)
		
	search_url = urlunparse(new_url)

	if search_url.endswith('/'): url = url[:-1]

	

	domain_obj = get_domain(domain)
	if not domain_obj: domain_obj = get_domain(domain+parsed_url.path)

	if domain_obj:
		reason = f"Remove the {domain_obj.domain} link from your post and try again. {domain_obj.reason}"
		return error(reason)
	elif "twitter.com" == domain:
		try: embed = requests.get("https://publish.twitter.com/oembed", params={"url":url, "omit_script":"t"}, timeout=5).json()["html"]
		except: pass
	elif url.startswith('https://youtube.com/watch?v='):
		url = unquote(url).replace('?t', '&t')
		yt_id = url.split('https://youtube.com/watch?v=')[1].split('&')[0].split('%')[0]

		if yt_id_regex.fullmatch(yt_id):
			req = requests.get(f"https://www.googleapis.com/youtube/v3/videos?id={yt_id}&key={YOUTUBE_KEY}&part=contentDetails", timeout=5).json()
			if req.get('items'):
				params = parse_qs(urlparse(url).query)
				t = params.get('t', params.get('start', [0]))[0]
				if isinstance(t, str): t = t.replace('s','')

				embed = f'<lite-youtube videoid="{yt_id}" params="autoplay=1&modestbranding=1'
				if t:
					try: embed += f'&start={int(t)}'
					except: pass
				embed += '"></lite-youtube>'
			
	elif app.config['SERVER_NAME'] in domain and "/post/" in url and "context" not in url:
		id = url.split("/post/")[1]
		if "/" in id: id = id.split("/")[0]
		embed = str(int(id))
