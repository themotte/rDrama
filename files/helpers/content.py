import random
import urllib.parse
from typing import TYPE_CHECKING, Any, Optional, Union

from sqlalchemy.orm import scoped_session

from files.helpers.const import PERMS

if TYPE_CHECKING:
	from files.classes import Comment, Submission, User
	Submittable = Union[Submission, Comment]
else:
	Comment = Any
	Submission = Any
	User = Any
	Submittable = Any


def _replace_urls(url:str) -> str:
	def _replace_extensions(url:str, exts:list[str]) -> str:
		for ext in exts:
			url = url.replace(f'.{ext}', '.webp')
		return url

	for rd in ("://reddit.com", "://new.reddit.com", "://www.reddit.com", "://redd.it", "://libredd.it", "://teddit.net"):
		url = url.replace(rd, "://old.reddit.com")

	url = url.replace("nitter.net", "twitter.com") \
		.replace("old.reddit.com/gallery", "reddit.com/gallery") \
		.replace("https://youtu.be/", "https://youtube.com/watch?v=") \
		.replace("https://music.youtube.com/watch?v=", "https://youtube.com/watch?v=") \
		.replace("https://streamable.com/", "https://streamable.com/e/") \
		.replace("https://youtube.com/shorts/", "https://youtube.com/watch?v=") \
		.replace("https://mobile.twitter", "https://twitter") \
		.replace("https://m.facebook", "https://facebook") \
		.replace("m.wikipedia.org", "wikipedia.org") \
		.replace("https://m.youtube", "https://youtube") \
		.replace("https://www.youtube", "https://youtube") \
		.replace("https://www.twitter", "https://twitter") \
		.replace("https://www.instagram", "https://instagram") \
		.replace("https://www.tiktok", "https://tiktok")

	if "/i.imgur.com/" in url:
		url = _replace_extensions(url, ['png', 'jpg', 'jpeg'])
	elif "/media.giphy.com/" in url or "/c.tenor.com/" in url:
		url = _replace_extensions(url, ['gif'])
	elif "/i.ibb.com/" in url: 
		url = _replace_extensions(url, ['png', 'jpg', 'jpeg', 'gif'])

	if url.startswith("https://streamable.com/") and not url.startswith("https://streamable.com/e/"): 
		url = url.replace("https://streamable.com/", "https://streamable.com/e/")
	return url

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


def canonicalize_url(url:str, *, httpsify:bool=False) -> str:
	return _replace_urls(url)

def canonicalize_url2(url:str, *, httpsify:bool=False) -> urllib.parse.ParseResult:
	url_parsed = _replace_urls(url)
	if httpsify: 
		url_parsed = _httpsify_and_remove_tracking_urls(url)
	else:
		url_parsed = urllib.parse.urlparse(url)
	return url_parsed


def moderated_body(target:Submittable, v:Optional[User]) -> Optional[str]:
	if v and (v.admin_level >= PERMS['POST_COMMENT_MODERATION'] \
			or v.id == target.author_id):
		return None
	if target.deleted_utc: return 'Deleted by author'
	if target.is_banned or target.filter_state == 'removed': return 'Removed'
	if target.filter_state == 'filtered': return 'Filtered'
	return None

def body_displayed(target:Submittable, v:Optional[User], is_html:bool) -> str:
	moderated:Optional[str] = moderated_body(target, v)
	if moderated: return moderated

	body = target.body_html if is_html else target.body
	if not body: return ""
	if not v: return body

	body = body.replace("old.reddit.com", v.reddit)
	if v.nitter and '/i/' not in body and '/retweets' not in body: 
		body = body.replace("www.twitter.com", "nitter.net").replace("twitter.com", "nitter.net")
	return body

def execute_shadowbanned_fake_votes(db:scoped_session, target:Submittable, v:Optional[User]):
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
