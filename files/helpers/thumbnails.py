'''
Fetching a link post's thumbnail, in the background after the post is made.
'''
import urllib.parse
from io import BytesIO
from typing import Optional

import requests
from bs4 import BeautifulSoup
from PIL import Image as PILimage

from files.__main__ import app, db_session
from files.classes.submission import Submission
from files.helpers.config.const import proxies
from files.helpers.config.environment import OUTBOUND_VERIFY
from files.helpers.media import UnreadableImage, new_image_path, process_image

titleheaders = {
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36"
}


def thumbnail_thread(pid):
	db = db_session()
	try:
		post = db.get(Submission, pid)
		if post and post.url: _fetch_thumbnail(db, post)
	finally:
		db.close()


THUMBNAIL_SOURCE_MAX_BYTES = 8 * 1024 * 1024
THUMBNAIL_SOURCE_MIN_SIDE = 30
# Parsing a page takes up to about 100 times its size in memory; preview images are named near the start
THUMBNAIL_PAGE_MAX_BYTES = 512 * 1024
# Decoding takes 3 to 4 bytes a pixel, so this bounds an image at about 64 MB in memory; a 100 px thumbnail needs no more
THUMBNAIL_SOURCE_MAX_PIXELS = 16_000_000
THUMBNAIL_MAX_CANDIDATES = 10
THUMBNAIL_META_TAGS = ["themotte:thumbnail", "twitter:image", "og:image", "thumbnail"]


def _fetch_thumbnail(db, post):
	page = _thumbnail_fetch(post.url)
	if not page or page[0].status_code != 200: return
	response, body = page

	content_type:str = response.headers.get("Content-Type", "")
	if content_type.startswith("text/html"):
		image = None
		for url in _thumbnail_candidates(post.url, body[:THUMBNAIL_PAGE_MAX_BYTES]):
			candidate = _thumbnail_fetch(url)
			if candidate and _thumbnail_suitable(*candidate):
				image = candidate[1]
				break
	elif content_type.startswith("image/") and _thumbnail_suitable(response, body):
		image = body
	else:
		return
	if image is None: return

	name = new_image_path()
	with open(name, "wb") as file:
		file.write(image)
	try:
		post.thumburl = process_image(name, resize=100)
	except UnreadableImage:
		app.logger.info("Thumbnail source for %s isn't an image that can be read whole", post.url)
		return
	db.add(post)
	db.commit()


def _thumbnail_fetch(url:str) -> Optional[tuple[requests.Response, bytes]]:
	'''The response and body at `url`, or None if it can't be fetched or is too large to be a thumbnail's source.'''
	try:
		with requests.get(url, headers=titleheaders, timeout=5, proxies=proxies, stream=True, verify=OUTBOUND_VERIFY) as response:
			body = bytearray()
			for chunk in response.iter_content(64 * 1024):
				body += chunk
				if len(body) > THUMBNAIL_SOURCE_MAX_BYTES:
					app.logger.info("Thumbnail source %s is over the size limit", url)
					return None
	except requests.RequestException as e:
		app.logger.info("Thumbnail source %s couldn't be fetched: %s", url, e)
		return None
	return response, bytes(body)


def _thumbnail_candidates(page_url:str, html:bytes) -> list[str]:
	'''Image addresses on a page, preview images named in its metadata first, resolved against the page and limited to web addresses.'''
	soup = BeautifulSoup(html, 'lxml')
	found:list[str] = []
	for tag_name in THUMBNAIL_META_TAGS:
		tag = soup.find('meta', attrs={"name": tag_name, "content": True}) or soup.find('meta', attrs={"property": tag_name, "content": True})
		if tag: found.append(tag['content'])
	found += [tag['src'] for tag in soup.find_all("img", attrs={'src': True})]
	resolved = (urllib.parse.urljoin(page_url, url) for url in found)
	return [url for url in resolved if url.startswith(("http://", "https://"))][:THUMBNAIL_MAX_CANDIDATES]


def _thumbnail_suitable(response:requests.Response, body:bytes) -> bool:
	content_type:str = response.headers.get("Content-Type", "")
	if response.status_code >= 400 or not content_type.startswith("image/") or content_type.startswith("image/svg"):
		return False
	try:
		image = PILimage.open(BytesIO(body))
		# Decoding allocates by the declared size, so refuse oversized images before decoding rather than after
		if image.width * image.height > THUMBNAIL_SOURCE_MAX_PIXELS:
			app.logger.info("Thumbnail source is %dx%d, too large to decode", image.width, image.height)
			return False
		image.load()
	except (OSError, PILimage.DecompressionBombError) as e:
		app.logger.info("Thumbnail source isn't a readable image: %s", e)
		return False
	return image.width >= THUMBNAIL_SOURCE_MIN_SIDE and image.height >= THUMBNAIL_SOURCE_MIN_SIDE
