import random
from typing import Any, TYPE_CHECKING, Optional, Union

from sqlalchemy.orm import scoped_session

from files.helpers.const import PERMS

if TYPE_CHECKING:
	from files.classes import Submission, Comment, User
	Submittable = Union[Submission, Comment]
else:
	Submission = Any
	Comment = Any
	User = Any
	Submittable = Any


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
