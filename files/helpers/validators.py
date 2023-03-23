import shutil
import time
import urllib.parse
from dataclasses import dataclass
from typing import NoReturn, Optional

from flask import Request, abort, request
from werkzeug.datastructures import FileStorage

import files.helpers.embeds as embeds
from files.helpers.config.environment import SITE_FULL, YOUTUBE_KEY
from files.helpers.config.const import (SUBMISSION_BODY_LENGTH_MAXIMUM,
                                 SUBMISSION_TITLE_LENGTH_MAXIMUM,
                                 SUBMISSION_URL_LENGTH_MAXIMUM)
from files.helpers.content import canonicalize_url2
from files.helpers.media import process_image
from files.helpers.sanitize import filter_emojis_only, sanitize, sanitize_raw


def guarded_value(val:str, min_len:int, max_len:int) -> str:
	'''
	Get request value `val` and ensure it is within length constraints
	Requires a request context and either aborts early or returns a good value
	'''
	raw = request.values.get(val, '').strip()
	raw = raw.replace('\u200e', '')

	if len(raw) < min_len: abort(400, f"Minimum length for {val} is {min_len}")
	if len(raw) > max_len: abort(400, f"Maximum length for {val} is {max_len}")
	# TODO: it may make sense to do more sanitisation here
	return raw


def int_ranged(val:str, min:int, max:int) -> int:
	def error() -> NoReturn:
		abort(400, 
			f"Invalid input ('{val}' must be an integer and be between {min} and {max})")

	raw:Optional[int] = request.values.get(val, default=None, type=int)
	if raw is None or raw < min or raw > max: error()
	return raw

@dataclass(frozen=True, kw_only=True, slots=True)
class ValidatedSubmissionLike:
	title: str
	title_html: str
	body: str
	body_raw: Optional[str]
	body_html: str
	url: Optional[str]
	thumburl: Optional[str]

	@property
	def embed_slow(self) -> Optional[str]:
		url:Optional[str] = self.url
		url_canonical: Optional[urllib.parse.ParseResult] = self.url_canonical
		if not url or not url_canonical: return None

		embed:Optional[str] = None
		domain:str = url_canonical.netloc

		if domain == "twitter.com":
			embed = embeds.twitter(url)
		
		if url.startswith('https://youtube.com/watch?v=') and YOUTUBE_KEY:
			embed = embeds.youtube(url)
			
		if SITE_FULL in domain and "/post/" in url and "context" not in url:
			id = url.split("/post/")[1]
			if "/" in id: id = id.split("/")[0]
			embed = str(int(id))

		return embed if embed and len(embed) <= 1500 else None

	@property
	def repost_search_url(self) -> Optional[str]:
		search_url = self.url_canonical_str
		if not search_url: return None

		if search_url.endswith('/'): 
			search_url = search_url[:-1]
		return search_url

	@property
	def url_canonical(self) -> Optional[urllib.parse.ParseResult]:
		if not self.url: return None
		return canonicalize_url2(self.url, httpsify=True)
	
	@property
	def url_canonical_str(self) -> Optional[str]:
		url_canonical:Optional[urllib.parse.ParseResult] = self.url_canonical
		if not url_canonical: return None
		return urllib.parse.urlunparse(url_canonical)

	@classmethod
	def from_flask_request(cls, 
			request:Request,
			*,
			allow_embedding:bool,
			allow_media_url_upload:bool=True,
			embed_url_file_key:str="file2",
			edit:bool=False) -> "ValidatedSubmissionLike":
		'''
		Creates the basic structure for a submission and validating it. The 
		normal submission API has a lot of duplicate code and while this is not
		a pretty solution, this essentially forces all submission-likes through
		a central interface.

		:param request: The Flask Request object.
		:param allow_embedding: Whether to allow embedding. This should usually
		be the value from the environment.
		:param allow_media_url_upload: Whether to allow media URL upload. This
		should generally be `True` for submission submitting if file uploads 
		are allowed and `False` in other contexts (such as editing)
		:param embed_url_file_key: The key to use for inline file uploads.
		:param edit: The value of `edit` to pass to `sanitize`
		'''

		def _process_media(file:Optional[FileStorage]) -> tuple[bool, Optional[str], Optional[str]]:
			if request.headers.get("cf-ipcountry") == "T1": return False, None, None
			if not file: return False, None, None
			if not file.content_length: return False, None, None 
			# handle bad browsers sending garbage
			if not file.content_type.startswith('image/'):
				abort(415, "Image files only")

			name = f'/images/{time.time()}'.replace('.','') + '.webp'
			file.save(name)
			url:Optional[str] = process_image(name)
			if not url: return False, None, None

			name2 = name.replace('.webp', 'r.webp')
			shutil.copyfile(name, name2)
			thumburl:Optional[str] = process_image(name2, resize=100)
			return True, url, thumburl

		def _process_media2(body:str, file2:Optional[list[FileStorage]]) -> tuple[bool, str]:
			if request.headers.get("cf-ipcountry") == "T1": return False, body # do not allow Tor uploads
			if not file2: return False, body
			file2 = file2[:4]
			if all(file.content_length == 0 for file in file2): 
				return False, body  # handle bad browsers sending garbage

			for file in file2:
				if not file.content_length:
					continue # handle bad browsers sending garbage
				if not file.content_type.startswith('image/'):
					abort(415, "Image files only")
				
				name = f'/images/{time.time()}'.replace('.','') + '.webp'
				file.save(name)
				image = process_image(name)
				if allow_embedding:
					body += f"\n\n![]({image})"
				else:
					body += f'\n\n<a href="{image}">{image}</a>'
			return True, body

		title = guarded_value("title", 1, SUBMISSION_TITLE_LENGTH_MAXIMUM)
		title = sanitize_raw(title, allow_newlines=False, length_limit=SUBMISSION_TITLE_LENGTH_MAXIMUM)

		url = guarded_value("url", 0, SUBMISSION_URL_LENGTH_MAXIMUM)
	
		body_raw = guarded_value("body", 0, SUBMISSION_BODY_LENGTH_MAXIMUM)
		body_raw = sanitize_raw(body_raw, allow_newlines=True, length_limit=SUBMISSION_BODY_LENGTH_MAXIMUM)

		if not url and allow_media_url_upload:
			has_file, url, thumburl = _process_media(request.files.get("file"))
		else:
			has_file = False
			thumburl = None

		has_file2, body = _process_media2(body_raw, request.files.getlist(embed_url_file_key))

		if not body_raw and not url and not has_file and not has_file2:
			raise ValueError("Please enter a URL or some text")
		
		title_html = filter_emojis_only(title, graceful=True)
		if len(title_html) > 1500:
			raise ValueError("Rendered title is too big!")
		
		return ValidatedSubmissionLike(
			title=title,
			title_html=filter_emojis_only(title, graceful=True),
			body=body,
			body_raw=body_raw,
			body_html=sanitize(body, edit=edit),
			url=url,
			thumburl=thumburl,
		)
