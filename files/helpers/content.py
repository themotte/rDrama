from __future__ import annotations

import random
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
