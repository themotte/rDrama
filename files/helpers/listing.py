"""
Module for listings.
"""

from typing import Optional

from flask import g, request
from sqlalchemy.sql.expression import and_, not_, or_
from sqlalchemy import false, func

from files.classes.comment import Comment
from files.classes.submission import Submission
from files.classes.user import User
from files.classes.visstate import StateMod
from files.classes.votes import Vote
from files.helpers.config.const import PERMS
from files.helpers.contentsorting import apply_time_filter, sort_objects
from files.helpers.strings import sql_ilike_clean


def _listable(items, cls, not_draft, v: Optional[User], admins_see_drafts_and_deleted: bool):
	# The permissions visibility_and_message checks: moderating for states and blocks, shadowbanning for shadowbans
	can_moderate = v and v.admin_level >= PERMS['POST_COMMENT_MODERATION']
	can_shadowban = v and v.admin_level >= PERMS['USER_SHADOWBAN']
	own = cls.author_id == v.id if v else false()
	if not (can_moderate and admins_see_drafts_and_deleted):
		items = items.filter(not_draft, cls.state_user_deleted_utc == None)
	if not can_moderate:
		items = items.filter(or_(own, cls.state_mod == StateMod.VISIBLE))
		if v: items = items.filter(cls.author_id.notin_(v.userblocks))
	if not can_shadowban:
		items = items.filter(or_(own, not_(cls.author.has(User.shadowbanned != None))))
	return items


def listable_posts(posts, v: Optional[User], *, admins_see_drafts_and_deleted: bool = False):
	'''
	`posts` (a query over submissions) narrowed to those `v` could read on their post pages: their own, and others that are visible, by an author who isn't shadowbanned and whom `v` doesn't block. Admins who moderate (level 2 and up) may read everything.

	Drafts and posts their authors deleted are left out for everyone, admins too unless `admins_see_drafts_and_deleted`.
	'''
	return _listable(posts, Submission, Submission.private == False, v, admins_see_drafts_and_deleted)


def listable_comments(comments, v: Optional[User], *, admins_see_drafts_and_deleted: bool = False):
	'''`comments` (a query over comments) narrowed to comments on posts that `v` could read in their threads, by the rule of `listable_posts`; comments on drafts count as drafts.'''
	comments = comments.filter(Comment.parent_submission != None)
	return _listable(comments, Comment, Comment.post.has(Submission.private == False), v, admins_see_drafts_and_deleted)


def changelog_post():
	'''The SQL condition for a changelog post: one by an admin (level 1 and up) whose title starts with "[changelog]" or "(changelog)", in any letter case.'''
	return or_(Submission.title.ilike('[changelog]%'), Submission.title.ilike('(changelog)%')) & Submission.author.has(User.account_admin_level >= 1)


def frontlist(v=None, sort='new', page=1, t="all", filter_words='', gt=0, lt=0):
	posts = g.db.query(Submission)
	
	if v and v.hidevotedon:
		voted = [x[0] for x in g.db.query(Vote.submission_id).filter_by(user_id=v.id).all()]
		posts = posts.filter(Submission.id.notin_(voted))

	posts = listable_posts(posts, v)

	if gt: posts = posts.filter(Submission.created_utc > gt)
	if lt: posts = posts.filter(Submission.created_utc < lt)

	if not gt and not lt:
		posts = apply_time_filter(posts, t, Submission)
		# The first page shows the pins above the rest
		posts = posts.filter(not_(Submission.pinned))

	if not (v and v.changelogsub):
		posts = posts.filter(not_(changelog_post()))

	if v and filter_words:
		for word in filter_words:
			word  = sql_ilike_clean(word).strip()
			posts = posts.filter(not_(Submission.title.ilike(f'%{word}%')))

	posts = sort_objects(posts, sort, Submission)

	if v:
		size = v.frontsize or 25
	else:
		size = 25

	posts = posts.offset(size * (page - 1)).limit(size+1).all()

	next_exists = (len(posts) > size)

	posts = posts[:size]

	if page == 1 and not gt and not lt:
		posts = listable_posts(g.db.query(Submission).filter(Submission.pinned), v).order_by(Submission.created_utc.desc(), Submission.id.desc()).all() + posts

	posts = [x.id for x in posts]

	return posts, next_exists


def request_page() -> int:
	'''The listing page the request asks for ("page"); anything but a whole number from 1 means the first.'''
	try: return max(1, int(request.values.get("page", 1)))
	except ValueError: return 1


def _userpage_posts(u:User, v:Optional[User]):
	'''The query for `u`'s posts that `v` may see on their profile, given that `u.shows_activity_to(v)`.'''
	posts = g.db.query(Submission.id).filter_by(author_id=u.id)

	if not (v and (v.admin_level >= 2 or v.id == u.id)):
		posts = posts.filter_by(state_user_deleted_utc=None, state_mod=StateMod.VISIBLE, private=False, ghost=False)

	return posts


def userpage_pinned(u:User, v:Optional[User]) -> list[int]:
	'''Ids of `u`'s pinned posts that `v` may see, newest first, given that `u.shows_activity_to(v)`.'''
	return [x[0] for x in _userpage_posts(u, v).filter_by(is_pinned=True).order_by(Submission.created_utc.desc()).all()]


# Whether `v` may see `u`'s posts at all (a shadowban) is decided by the caller
def userpagelisting(u:User, v=None, page=1, sort="new", t="all"):
	posts = _userpage_posts(u, v).filter_by(is_pinned=False)
	posts = apply_time_filter(posts, t, Submission)
	posts = sort_objects(posts, sort, Submission)

	posts = posts.offset(25 * (page - 1)).limit(26).all()

	return [x[0] for x in posts]


def changeloglist(v=None, sort="new", page=1, t="all"):
	posts = listable_posts(g.db.query(Submission.id), v)

	posts = posts.filter(changelog_post())

	if t != 'all':
		posts = apply_time_filter(posts, t, Submission)
	posts = sort_objects(posts, sort, Submission)

	posts = posts.offset(25 * (page - 1)).limit(26).all()

	return [x[0] for x in posts]
