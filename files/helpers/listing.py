"""
Module for listings.
"""

import time
from operator import not_

from flask import g

from files.__main__ import cache
from files.classes.submission import Submission
from files.classes.user import User
from files.classes.votes import Vote
from files.helpers.contentsorting import apply_time_filter, sort_objects
from files.helpers.strings import sql_ilike_clean


@cache.memoize(timeout=86400)
def frontlist(v=None, sort='new', page=1, t="all", ids_only=True, ccmode="false", filter_words='', gt=0, lt=0, sub=None, site=None):
	posts = g.db.query(Submission)
	
	if v and v.hidevotedon:
		voted = [x[0] for x in g.db.query(Vote.submission_id).filter_by(user_id=v.id).all()]
		posts = posts.filter(Submission.id.notin_(voted))

	if not v or v.admin_level < 2:
		filter_clause = (Submission.filter_state != 'filtered') & (Submission.filter_state != 'removed')
		if v:
			filter_clause = filter_clause | (Submission.author_id == v.id)
		posts = posts.filter(filter_clause)

	if sub: posts = posts.filter_by(sub=sub.name)
	elif v: posts = posts.filter((Submission.sub == None) | Submission.sub.notin_(v.all_blocks))

	if gt: posts = posts.filter(Submission.created_utc > gt)
	if lt: posts = posts.filter(Submission.created_utc < lt)

	if not gt and not lt:
		posts = apply_time_filter(posts, t, Submission)

	if (ccmode == "true"):
		posts = posts.filter(Submission.club == True)

	posts = posts.filter_by(is_banned=False, private=False, deleted_utc = 0)

	if ccmode == "false" and not gt and not lt:
		posts = posts.filter_by(stickied=None)

	if v and v.admin_level < 2:
		posts = posts.filter(Submission.author_id.notin_(v.userblocks))

	if not (v and v.changelogsub):
		posts=posts.filter(not_(Submission.title.ilike('[changelog]%')))

	if v and filter_words:
		for word in filter_words:
			word  = sql_ilike_clean(word).strip()
			posts=posts.filter(not_(Submission.title.ilike(f'%{word}%')))

	if not (v and v.shadowbanned):
		posts = posts.join(User, User.id == Submission.author_id).filter(User.shadowbanned == None)

	posts = sort_objects(posts, sort, Submission)

	size = v.frontsize or 25

	posts = posts.offset(size * (page - 1)).limit(size+1).all()

	next_exists = (len(posts) > size)

	posts = posts[:size]

	if page == 1 and ccmode == "false" and not gt and not lt:
		pins = g.db.query(Submission).filter(Submission.stickied != None, Submission.is_banned == False)
		if sub: pins = pins.filter_by(sub=sub.name)
		elif v:
			pins = pins.filter(Submission.sub == None | Submission.sub.notin_(v.all_blocks))
			if v.admin_level < 2:
				pins = pins.filter(Submission.author_id.notin_(v.userblocks))

		pins = pins.all()

		for pin in pins:
			if pin.stickied_utc and int(time.time()) > pin.stickied_utc:
				pin.stickied = None
				pin.stickied_utc = None
				g.db.add(pin)
				pins.remove(pin)

		posts = pins + posts

	if ids_only: posts = [x.id for x in posts]

	g.db.commit()

	return posts, next_exists


@cache.memoize(timeout=86400)
def userpagelisting(self, site=None, v=None, page=1, sort="new", t="all"):
	if self.shadowbanned and not (v and (v.admin_level > 1 or v.id == self.id)): return []

	posts = g.db.query(Submission.id).filter_by(author_id=self.id, is_pinned=False)

	if not (v and (v.admin_level > 1 or v.id == self.id)):
		posts = posts.filter_by(deleted_utc=0, is_banned=False, private=False, ghost=False)

	posts = apply_time_filter(posts, t, Submission)
	posts = sort_objects(posts, sort, Submission)

	posts = posts.offset(25 * (page - 1)).limit(26).all()

	return [x[0] for x in posts]

@cache.memoize(timeout=86400)
def changeloglist(v=None, sort="new", page=1, t="all", site=None):
	posts = g.db.query(Submission.id).filter_by(is_banned=False, private=False,).filter(Submission.deleted_utc == 0)

	if v.admin_level < 2:
		posts = posts.filter(Submission.author_id.notin_(v.userblocks))

	admins = [x[0] for x in g.db.query(User.id).filter(User.admin_level > 0).all()]
	posts = posts.filter(Submission.title.ilike('_changelog%'), Submission.author_id.in_(admins))

	if t != 'all':
		posts = apply_time_filter(posts, t, Submission)
	posts = sort_objects(posts, sort, Submission)

	posts = posts.offset(25 * (page - 1)).limit(26).all()

	return [x[0] for x in posts]