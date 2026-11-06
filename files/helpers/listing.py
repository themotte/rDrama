"""
Module for listings.
"""

import time
from typing import Optional

from flask import g, request
from sqlalchemy.sql.expression import not_
from sqlalchemy import func

from files.classes.submission import Submission
from files.classes.user import User
from files.classes.visstate import StateMod
from files.classes.votes import Vote
from files.helpers.contentsorting import apply_time_filter, sort_objects
from files.helpers.strings import sql_ilike_clean


def frontlist(v=None, sort='new', page=1, t="all", filter_words='', gt=0, lt=0):
	posts = g.db.query(Submission)
	
	if v and v.hidevotedon:
		voted = [x[0] for x in g.db.query(Vote.submission_id).filter_by(user_id=v.id).all()]
		posts = posts.filter(Submission.id.notin_(voted))

	if not v or v.admin_level < 2:
		filter_clause = Submission.state_mod == StateMod.VISIBLE
		if v:
			filter_clause = filter_clause | (Submission.author_id == v.id)
		posts = posts.filter(filter_clause)

	if gt: posts = posts.filter(Submission.created_utc > gt)
	if lt: posts = posts.filter(Submission.created_utc < lt)

	if not gt and not lt:
		posts = apply_time_filter(posts, t, Submission)
		# The first page shows the pins above the rest
		posts = posts.filter(not_((Submission.stickied != None) & ((Submission.stickied_utc == None) | (Submission.stickied_utc >= int(time.time())))))

	posts = posts.filter_by(private=False, state_user_deleted_utc=None)

	if v and v.admin_level < 2:
		posts = posts.filter(Submission.author_id.notin_(v.userblocks))

	if not (v and v.changelogsub):
		posts = posts.filter(not_(Submission.title.ilike('[changelog]%')))

	if v and filter_words:
		for word in filter_words:
			word  = sql_ilike_clean(word).strip()
			posts = posts.filter(not_(Submission.title.ilike(f'%{word}%')))

	if not (v and v.shadowbanned):
		posts = posts.join(User, User.id == Submission.author_id).filter(User.shadowbanned == None)

	posts = sort_objects(posts, sort, Submission)

	if v:
		size = v.frontsize or 25
	else:
		size = 25

	posts = posts.offset(size * (page - 1)).limit(size+1).all()

	next_exists = (len(posts) > size)

	posts = posts[:size]

	if page == 1 and not gt and not lt:
		pins = g.db.query(Submission).filter(Submission.stickied != None, Submission.state_mod == StateMod.VISIBLE)
		if v:
			if v.admin_level < 2:
				pins = pins.filter(Submission.author_id.notin_(v.userblocks))

		pins = pins.all()

		for pin in pins:
			if pin.stickied_utc and int(time.time()) > pin.stickied_utc:
				pin.stickied = None
				pin.stickied_utc = None
				g.db.add(pin)
				pins.remove(pin)
				g.db.commit()

		posts = pins + posts

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
	posts = g.db.query(Submission.id).filter_by(state_mod=StateMod.VISIBLE, private=False,).filter(Submission.state_user_deleted_utc == None)

	if v.admin_level < 2:
		posts = posts.filter(Submission.author_id.notin_(v.userblocks))

	admins = [x[0] for x in g.db.query(User.id).filter(User.admin_level > 0).all()]
	posts = posts.filter(Submission.title.ilike('_changelog%'), Submission.author_id.in_(admins))

	if t != 'all':
		posts = apply_time_filter(posts, t, Submission)
	posts = sort_objects(posts, sort, Submission)

	posts = posts.offset(25 * (page - 1)).limit(26).all()

	return [x[0] for x in posts]
