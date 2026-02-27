from __future__ import annotations

import random
import re
import urllib.parse
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy.orm import Session

if TYPE_CHECKING:
	from files.classes import Comment, Submission, User
	Submittable = Comment | Submission
else:
	Submittable = Any




def _httpsify_and_remove_tracking_urls(url:str) -> urllib.parse.ParseResult:
	parsed_url = urllib.parse.urlparse(url)
	domain = parsed_url.netloc
	is_reddit_twitter_instagram_tiktok:bool = domain in \
		('old.reddit.com','twitter.com','instagram.com','tiktok.com')

	if is_reddit_twitter_instagram_tiktok:
		query = ""
	else:
		qd = urllib.parse.parse_qs(parsed_url.query)
		filtered = {k: val for k, val in qd.items() if not k.startswith('utm_') and not k.startswith('ref_')}
		query = urllib.parse.urlencode(filtered, doseq=True)
	
	new_url = urllib.parse.ParseResult(
		scheme="https",
		netloc=parsed_url.netloc,
		path=parsed_url.path,
		params=parsed_url.params,
		query=query,
		fragment=parsed_url.fragment,
	)
	return new_url




def canonicalize_url2(url:str, *, httpsify:bool=False) -> urllib.parse.ParseResult:
	if httpsify:
		url_parsed = _httpsify_and_remove_tracking_urls(url)
	else:
		url_parsed = urllib.parse.urlparse(url)
	return url_parsed


def _is_external_link(href:str) -> bool:
	"""Check if a link is external (not to this site)."""
	from files.helpers.config.environment import SITE_FULL
	if not href:
		return False
	if href.startswith('/'):
		return False
	if href.startswith(f'{SITE_FULL}/'):
		return False
	if href.startswith('#'):
		return False
	return True


# Regex to match <a ...> tags. We use a non-greedy match on the attributes.
_A_TAG_RE = re.compile(r'(<a\s)(.*?)(>)', re.DOTALL | re.IGNORECASE)
_TARGET_BLANK_RE = re.compile(r'\s*target\s*=\s*"_blank"\s*', re.IGNORECASE)
_HREF_RE = re.compile(r'href\s*=\s*"([^"]*)"', re.IGNORECASE)


def _apply_newtab_settings(body:str, newtab:bool, newtabexternal:bool) -> str:
	"""
	Adjust target="_blank" on links in rendered HTML body content
	based on the viewing user's newtab/newtabexternal settings.

	The sanitizer always adds target="_blank" to external links at
	content-creation time. This function corrects that per-viewer:
	- If newtabexternal is False, remove target="_blank" from external links
	- If newtab is True, add target="_blank" to internal links
	"""
	# Default settings (newtab=False, newtabexternal=True) match what the
	# sanitizer already does, so we can skip processing entirely.
	if not newtab and newtabexternal:
		return body

	def _replace_a_tag(match):
		prefix = match.group(1)  # '<a '
		attrs = match.group(2)   # everything between '<a ' and '>'
		suffix = match.group(3)  # '>'

		href_match = _HREF_RE.search(attrs)
		if not href_match:
			return match.group(0)

		href = href_match.group(1)
		is_external = _is_external_link(href)
		has_target_blank = _TARGET_BLANK_RE.search(attrs)

		if is_external and not newtabexternal and has_target_blank:
			# Remove target="_blank" from external links
			attrs = _TARGET_BLANK_RE.sub(' ', attrs).strip()
		elif not is_external and newtab and not has_target_blank:
			# Add target="_blank" to internal links
			attrs = f'{attrs} target="_blank"'

		return f'{prefix}{attrs}{suffix}'

	return _A_TAG_RE.sub(_replace_a_tag, body)


def body_displayed(target:Submittable, v:Optional[User], is_html:bool) -> str:
	added_message = target.visibility_state.added_message(v)

	if is_html:
		body = target.body_html
		if not body: return ""
		if not v: return body

		if added_message:
			body = f'{body}<div class="visibility-message">{added_message}</div>'
	else:
		body = target.body
		if not body: return ""
		if not v: return body

		if added_message:
			body = f'{body}\n\n{added_message}'

	body = body.replace("old.reddit.com", v.reddit)
	if v.nitter and '/i/' not in body and '/retweets' not in body:
		body = body.replace("www.twitter.com", "nitter.net").replace("twitter.com", "nitter.net")

	if is_html:
		body = _apply_newtab_settings(body, v.newtab, v.newtabexternal)

	return body


def execute_shadowbanned_fake_votes(db:Session, target:Submittable, v:Optional[User]):
	if not target or not v: return
	if not v.shadowbanned: return
	if v.id != target.author_id: return
	if not (86400 > target.age_seconds > 20): return

	ti = max(target.age_seconds // 60, 1)
	maxupvotes = min(ti, 11)
	rand = random.randint(0, maxupvotes)
	if target.upvotes >= rand: return

	amount = random.randint(0, 3)
	if amount != 1: return
	
	if hasattr(target, 'views'):
		target.views += amount*random.randint(3, 5)
	
	target.upvotes += amount
	db.add(target)
	db.commit()
