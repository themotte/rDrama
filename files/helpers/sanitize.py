import bleach
from bs4 import BeautifulSoup
from bleach.linkifier import LinkifyFilter
from functools import partial
from .get import *
from .patter import pat
from os import path, environ
import re
from mistletoe import markdown
from json import loads, dump
from random import random, choice
import signal
import time
import requests

def callback(attrs, new=False):
	href = attrs[(None, "href")]

	if not href.startswith(SITE_FULL) and not href.startswith('/') and not href.startswith(SITE_FULL2):
		attrs[(None, "target")] = "_blank"
		attrs[(None, "rel")] = "nofollow noopener noreferrer"	

	return attrs


def sanitize(sanitized, noimages=False, alert=False, comment=False, edit=False):

	def handler(signum, frame):
		print("Timeout!")
		raise Exception("Timeout")

	signal.signal(signal.SIGALRM, handler)
	signal.alarm(1)

	sanitized = image_check_regex.sub(r'\1', sanitized)

	sanitized = markdown(sanitized)

	sanitized = strikethrough_regex.sub(r'<del>\1</del>', sanitized)

	sanitized = sanitized.replace('‎','').replace('​','').replace("\ufeff", "").replace("𒐪","")

	if alert:
		captured = []
		for i in mention_regex2.finditer(sanitized):
			if i.group(0) in captured: continue
			captured.append(i.group(0))

			u = get_user(i.group(1), graceful=True)
			if u:
				sanitized = sanitized.replace(i.group(0), f'''<p><a href="/id/{u.id}"><img loading="lazy" src="/pp/{u.id}">@{u.username}</a>''')
	else:
		sanitized = reddit_regex.sub(r'\1<a href="https://old.reddit.com/\2" rel="nofollow noopener noreferrer">/\2</a>', sanitized)

		sanitized = sub_regex.sub(r'\1<a href="/\2">/\2</a>', sanitized)

		captured = []
		for i in mention_regex.finditer(sanitized):
			if i.group(0) in captured: continue
			captured.append(i.group(0))

			u = get_user(i.group(2), graceful=True)

			if u and (not g.v.any_block_exists(u) or g.v.admin_level > 1):
				sanitized = sanitized.replace(i.group(0), f'''{i.group(1)}<a href="/id/{u.id}"><img loading="lazy" src="/pp/{u.id}">@{u.username}</a>''')


	sanitized = imgur_regex.sub(r'\1_d.webp?maxwidth=9999&fidelity=high', sanitized)

	soup = BeautifulSoup(sanitized, 'lxml')

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
	
	if comment: marseys_used = set()

	emojis = list(emoji_regex.finditer(sanitized))
	if len(emojis) > 20: edit = True

	captured = []
	for i in emojis:
		if i.group(0) in captured: continue
		captured.append(i.group(0))

		old = i.group(0)
		if 'marseylong1' in old or 'marseylong2' in old or 'marseyllama1' in old or 'marseyllama2' in old: new = old.lower().replace(">", " class='mb-0'>")
		else: new = old.lower()

		captured2 = []
		for i in emoji_regex2.finditer(new):
			if i.group(0) in captured2: continue
			captured2.append(i.group(0))

			emoji = i.group(1).lower()
			remoji = emoji.replace('!','').replace('#','')

			golden = ' '
			if not edit and random() < 0.0025 and ('marsey' in emoji or emoji in marseys_const2): golden = 'g '

			if remoji == 'marseyrandom': remoji = choice(marseys_const2)

			if path.isfile(f'files/assets/images/emojis/{remoji}.webp'):
				new = re.sub(f'(?<!"):{emoji}:', f'<img loading="lazy" data-bs-toggle="tooltip" alt=":{emoji}:" title=":{emoji}:" b {golden}src="/e/{remoji}.webp">', new, flags=re.I|re.A)
				if comment: marseys_used.add(emoji)
			elif remoji.endswith('pat') and path.isfile(f"files/assets/images/emojis/{remoji.replace('pat','')}.webp"):
				pat(remoji.replace('pat',''))
				new = re.sub(f'(?<!"):{emoji}:', f'<img loading="lazy" data-bs-toggle="tooltip" alt=":{emoji}:" title=":{emoji}:" b {golden}src="/e/{remoji}.webp">', new, flags=re.I|re.A)
				requests.post(f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE}/purge_cache', headers=CF_HEADERS, data={'files': [f"https://{request.host}/e/{emoji}.webp"]}, timeout=5)


		sanitized = sanitized.replace(old, new)

	emojis = list(emoji_regex3.finditer(sanitized))
	if len(emojis) > 20: edit = True

	captured = []
	for i in emojis:
		if i.group(0) in captured: continue
		captured.append(i.group(0))

		emoji = i.group(1).lower()
		golden = ' '
		if not edit and random() < 0.0025 and ('marsey' in emoji or emoji in marseys_const2): golden = 'g '

		old = emoji
		emoji = emoji.replace('!','').replace('#','')
		if emoji == 'marseyrandom': emoji = choice(marseys_const2)


		if path.isfile(f'files/assets/images/emojis/{emoji}.webp'):
			sanitized = re.sub(f'(?<!"):{i.group(1).lower()}:', f'<img loading="lazy" data-bs-toggle="tooltip" alt=":{old}:" title=":{old}:" {golden}src="/e/{emoji}.webp">', sanitized, flags=re.I|re.A)
			if comment: marseys_used.add(emoji)
		elif emoji.endswith('pat') and path.isfile(f"files/assets/images/emojis/{emoji.replace('pat','')}.webp"):
			pat(emoji.replace('pat',''))
			sanitized = re.sub(f'(?<!"):{i.group(1).lower()}:', f'<img loading="lazy" data-bs-toggle="tooltip" alt=":!{old}:" title=":!{old}:" {golden}src="/e/{emoji}.webp">', sanitized, flags=re.I|re.A)
			requests.post(f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE}/purge_cache', headers=CF_HEADERS, data={'files': [f"https://{request.host}/e/{emoji}.webp"]}, timeout=5)


	for rd in ["://reddit.com", "://new.reddit.com", "://www.reddit.com", "://redd.it", "://libredd.it", "://teddit.net"]:
		sanitized = sanitized.replace(rd, "://old.reddit.com")

	sanitized = sanitized.replace("nitter.net", "twitter.com").replace("old.reddit.com/gallery", "reddit.com/gallery").replace("https://youtu.be/", "https://youtube.com/watch?v=").replace("https://music.youtube.com/watch?v=", "https://youtube.com/watch?v=").replace("https://streamable.com/", "https://streamable.com/e/").replace("https://youtube.com/shorts/", "https://youtube.com/watch?v=").replace("https://mobile.twitter", "https://twitter").replace("https://m.facebook", "https://facebook").replace("m.wikipedia.org", "wikipedia.org").replace("https://m.youtube", "https://youtube").replace("https://www.youtube", "https://youtube").replace("https://www.twitter", "https://twitter").replace("https://www.instagram", "https://instagram").replace("https://www.tiktok", "https://tiktok")


	if "https://youtube.com/watch?v=" in sanitized: sanitized = sanitized.replace("?t=", "&t=")

	captured = []
	for i in youtube_regex.finditer(sanitized):
		url = i.group(0)
		if url in captured: continue
		captured.append(url)

		params = parse_qs(urlparse(url.replace('&amp;','&')).query)
		t = params.get('t', params.get('start', [0]))[0]
		if isinstance(t, str): t = t.replace('s','')

		htmlsource = f'<lite-youtube videoid="{i.group(1)}" params="autoplay=1&modestbranding=1'
		if t: htmlsource += f'&start={t}'
		htmlsource += '"></lite-youtube>'

		sanitized = sanitized.replace(url, htmlsource)


	sanitized = unlinked_regex.sub(r'\1<a href="\2" rel="nofollow noopener noreferrer" target="_blank">\2</a>', sanitized)

	if not noimages:
		sanitized = video_regex.sub(r'<p><video controls preload="none"><source src="\1"></video>', sanitized)

	if comment:
		for marsey in g.db.query(Marsey).filter(Marsey.name.in_(marseys_used)).all():
			marsey.count += 1
			g.db.add(marsey)

	if '#fortune' in sanitized:
		sanitized = sanitized.replace('#fortune', '')
		sanitized += '\n\n<p>' + choice(FORTUNE_REPLIES) + '</p>'

	sanitized = sanitized.replace('&amp;','&')
	sanitized = utm_regex.sub('', sanitized)
	sanitized = utm_regex2.sub('', sanitized)


	sanitized = sanitized.replace('<html><body>','').replace('</body></html>','')


	allowed_tags = ['b','blockquote','br','code','del','em','h1','h2','h3','h4','h5','h6','hr','i','li','ol','p','pre','strong','sub','sup','table','tbody','th','thead','td','tr','ul','marquee','a','span','ruby','rp','rt','spoiler','img','lite-youtube']
	if not noimages: allowed_tags += ['video','source']

	def allowed_attributes(tag, name, value):

		if name == 'style': return True

		if tag == 'marquee':
			if name in ['direction', 'behavior', 'scrollamount']: return True
			if name in {'height', 'width'}:
				try: value = int(value.replace('px', ''))
				except: return False
				if 0 < value <= 250: return True
			return False
		
		if tag == 'a':
			if name == 'href': return True
			if name == 'rel' and value == 'nofollow noopener noreferrer': return True
			if name == 'target' and value == '_blank': return True
			return False

		if tag == 'img':
			if name in ['src','data-src'] and not value.startswith('/') and noimages: return False

			if name == 'loading' and value == 'lazy': return True
			if name == 'referrpolicy' and value == 'no-referrer': return True
			if name == 'data-bs-toggle' and value == 'tooltip': return True
			if name in ['src','data-src','alt','title','g','b']: return True
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
			if name == 'src': return True
			return False

		if tag == 'p':
			if name == 'class' and value == 'mb-0': return True
			return False


	sanitized = bleach.Cleaner(tags=allowed_tags,
								attributes=allowed_attributes,
								protocols=['http', 'https'],
								styles=['color', 'background-color', 'font-weight', 'text-align'],
								filters=[partial(LinkifyFilter, skip_tags=["pre"], parse_email=False, callbacks=[callback])]
								).clean(sanitized)



	signal.alarm(0)

	return sanitized





def filter_emojis_only(title, edit=False, graceful=False):

	def handler(signum, frame):
		print("Timeout!")
		raise Exception("Timeout")

	signal.signal(signal.SIGALRM, handler)
	signal.alarm(1)
	
	title = title.replace('‎','').replace('​','').replace("\ufeff", "").replace("𒐪","").replace("\n", "").replace("\r", "").replace("\t", "").replace("&", "&amp;").replace('<','&lt;').replace('>','&gt;').replace('"', '&quot;').replace("'", "&#039;").strip()

	emojis = list(emoji_regex4.finditer(title))
	if len(emojis) > 20: edit = True

	captured = []
	for i in emojis:
		if i.group(0) in captured: continue
		captured.append(i.group(0))

		emoji = i.group(1).lower()
		golden = ' '
		if not edit and random() < 0.0025 and ('marsey' in emoji or emoji in marseys_const2): golden = 'g '

		old = emoji
		emoji = emoji.replace('!','').replace('#','')
		if emoji == 'marseyrandom': emoji = choice(marseys_const2)		

		if path.isfile(f'files/assets/images/emojis/{emoji}.webp'):
			title = re.sub(f'(?<!"):{old}:', f'<img loading="lazy" data-bs-toggle="tooltip" alt=":{old}:" title=":{old}:" {golden}src="/e/{emoji}.webp">', title, flags=re.I|re.A)
		elif emoji.endswith('pat') and path.isfile(f"files/assets/images/emojis/{emoji.replace('pat','')}.webp"):
			pat(emoji.replace('pat',''))
			title = re.sub(f'(?<!"):{old}:', f'<img loading="lazy" data-bs-toggle="tooltip" alt=":{old}:" title=":{old}:" {golden}src="/e/{emoji}.webp">', title, flags=re.I|re.A)
			requests.post(f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE}/purge_cache', headers=CF_HEADERS, data={'files': [f"https://{request.host}/e/{emoji}.webp"]}, timeout=5)


	title = strikethrough_regex.sub(r'<del>\1</del>', title)


	def allowed_attributes(tag, name, value):

		if tag == 'img':
			if name == 'loading' and value == 'lazy': return True
			if name == 'data-bs-toggle' and value == 'tooltip': return True
			if name in ['src','alt','title','g']: return True
			return False


	sanitized = bleach.clean(title, tags=['img','del'], attributes=allowed_attributes, protocols=['http','https'])

	signal.alarm(0)

	if len(title) > 1500 and not graceful: abort(400)
	else: return title