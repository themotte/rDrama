import shutil
import urllib.parse
from dataclasses import dataclass
from typing import Optional

from flask import Request, abort, request
from werkzeug.datastructures import FileStorage

import files.helpers.sanitize as sanitize
from files.helpers.config.const import (SUBMISSION_BODY_LENGTH_MAXIMUM,
                                 SUBMISSION_TITLE_LENGTH_MAXIMUM,
                                 SUBMISSION_URL_LENGTH_MAXIMUM)
from files.helpers.content import canonicalize_url2, is_web_url
from files.helpers.media import attach_images, new_image_path, process_image


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
	raw:Optional[int] = request.values.get(val, default=None, type=int)
	if raw is None or raw < min or raw > max:
		abort(400, 
			f"Invalid input ('{val}' must be an integer and be between {min} and {max})")
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
	def url_canonical(self) -> Optional[urllib.parse.ParseResult]:
		if not self.url: return None
		return canonicalize_url2(self.url, httpsify=True)

	@classmethod
	def from_flask_request(cls, 
			request:Request,
			*,
			allow_media_url_upload:bool=True,
			embed_url_file_key:str="file2",
			existing_url:Optional[str]=None) -> "ValidatedSubmissionLike":
		'''
		Creates the basic structure for a submission and validating it. The 
		normal submission API has a lot of duplicate code and while this is not
		a pretty solution, this essentially forces all submission-likes through
		a central interface.

		:param request: The Flask Request object.
		:param allow_media_url_upload: Whether to allow media URL upload. This
		should generally be `True` for submission submitting if file uploads 
		are allowed and `False` in other contexts (such as editing)
		:param embed_url_file_key: The key to use for inline file uploads.
		:param existing_url: The link of the submission being edited, which
		counts as content even though the edit form doesn't send it.
		'''

		def _process_media(file:Optional[FileStorage]) -> tuple[bool, Optional[str], Optional[str]]:
			if not file:
				# We actually care about falseyness, not just `is not None` because
				# no attachment is <FileStorage: '' ('application/octet-stream')>
				# (at least from Firefox 111).
				return False, None, None
			elif not file.content_type.startswith('image/'):
				abort(415, "Image files only")

			name = new_image_path()
			file.save(name)
			url:str = process_image(name)

			name2 = name.replace('.webp', 'r.webp')
			shutil.copyfile(name, name2)
			thumburl:Optional[str] = process_image(name2, resize=100)
			return True, url, thumburl

		title = guarded_value("title", 1, SUBMISSION_TITLE_LENGTH_MAXIMUM)
		title = sanitize.sanitize_raw(title, allow_newlines=False, length_limit=SUBMISSION_TITLE_LENGTH_MAXIMUM)
		title_html = sanitize.filter_emojis_only(title)
		if not title_html.strip():
			abort(400, "The title has no visible text")

		url = guarded_value("url", 0, SUBMISSION_URL_LENGTH_MAXIMUM)
		if url and not is_web_url(url):
			abort(400, "Links must be web addresses starting with http:// or https://")
	
		body_raw = guarded_value("body", 0, SUBMISSION_BODY_LENGTH_MAXIMUM)
		body_raw = sanitize.sanitize_raw(body_raw, allow_newlines=True, length_limit=SUBMISSION_BODY_LENGTH_MAXIMUM)

		if not url and allow_media_url_upload:
			has_file, url, thumburl = _process_media(request.files.get("file"))
		else:
			has_file = False
			thumburl = None

		has_file2, body = attach_images(body_raw, request.files.getlist(embed_url_file_key))
		if len(body) > SUBMISSION_BODY_LENGTH_MAXIMUM:
			abort(400, f"Maximum length for body is {SUBMISSION_BODY_LENGTH_MAXIMUM}, including the links to attached images")

		if not body_raw and not url and not existing_url and not has_file and not has_file2:
			abort(400, "Please enter a URL or some text")
		
		return ValidatedSubmissionLike(
			title=title,
			title_html=title_html,
			body=body,
			body_raw=body_raw,
			body_html=sanitize.sanitize(body),
			url=url,
			thumburl=thumburl,
		)
