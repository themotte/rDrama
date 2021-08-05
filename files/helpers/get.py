from files.classes import *
from flask import g
from sqlalchemy.orm import joinedload, aliased

import re


def get_user(username, v=None, graceful=False):

	username = username.replace('\\', '')
	username = username.replace('_', '\_')
	username = username.replace('%', '')

	user = g.db.query(
		User
		).filter(
		or_(
			User.username.ilike(username),
			User.original_username.ilike(username)
			)
		).first()

	if not user:
		if not graceful:
			abort(404)
		else:
			return None

	if v:
		block = g.db.query(UserBlock).filter(
			or_(
				and_(
					UserBlock.user_id == v.id,
					UserBlock.target_id == user.id
				),
				and_(UserBlock.user_id == user.id,
					 UserBlock.target_id == v.id
					 )
			)
		).first()

		user._is_blocking = block and block.user_id == v.id
		user._is_blocked = block and block.target_id == v.id

	return user

def get_account(id, v=None):

	user = g.db.query(User).filter_by(id = id).first()
				
	if not user:
		try: id = int(str(id), 36)
		except: abort(404)
		user = g.db.query(User).filter_by(id = id).first()
		if not user: abort(404)

	if v:
		block = g.db.query(UserBlock).filter(
			or_(
				and_(
					UserBlock.user_id == v.id,
					UserBlock.target_id == user.id
				),
				and_(UserBlock.user_id == user.id,
					 UserBlock.target_id == v.id
					 )
			)
		).first()

		user._is_blocking = block and block.user_id == v.id
		user._is_blocked = block and block.target_id == v.id

	return user


def get_post(i, v=None, graceful=False, **kwargs):

	if v:
		vt = g.db.query(Vote).filter_by(
			user_id=v.id, submission_id=i).subquery()
		blocking = v.blocking.subquery()

		items = g.db.query(
			Submission,
			vt.c.vote_type,
			blocking.c.id,
		)

		if v.admin_level>=4:
			items=items.options(joinedload(Submission.oauth_app))
		items=items.filter(Submission.id == i
		).join(
			vt, 
			vt.c.submission_id == Submission.id, 
			isouter=True
		).join(
			blocking, 
			blocking.c.target_id == Submission.author_id, 
			isouter=True
		)

		items=items.first()

		if not items and not graceful:
			abort(404)
		x = items[0]
		x._voted = items[1] or 0
		x._is_blocking = items[2] or 0
	else:
		items = g.db.query(
			Submission
		).filter(Submission.id == i).first()
		if not items and not graceful:
			abort(404)
		x=items

	return x


def get_posts(pids, v=None):

	if not pids:
		return []

	pids=tuple(pids)

	if v:
		vt = g.db.query(Vote).filter(
			Vote.submission_id.in_(pids), 
			Vote.user_id==v.id
			).subquery()

		blocking = v.blocking.subquery()
		blocked = v.blocked.subquery()

		query = g.db.query(
			Submission,
			vt.c.vote_type,
			blocking.c.id,
			blocked.c.id,
		).filter(
			Submission.id.in_(pids)
		).join(
			vt, vt.c.submission_id==Submission.id, isouter=True
		).join(
			blocking, 
			blocking.c.target_id == Submission.author_id, 
			isouter=True
		).join(
			blocked, 
			blocked.c.user_id == Submission.author_id, 
			isouter=True
		).all()

		output = [p[0] for p in query]
		for i in range(len(output)):
			output[i]._voted = query[i][1] or 0
			output[i]._is_blocking = query[i][2] or 0
			output[i]._is_blocked = query[i][3] or 0
	else:
		output = g.db.query(
			Submission,
		).filter(Submission.id.in_(pids)
		).all()

	return sorted(output, key=lambda x: pids.index(x.id))

def get_comment(i, v=None, graceful=False, **kwargs):

	if v:
		blocking = v.blocking.subquery()
		blocked = v.blocked.subquery()

		items = g.db.query(Comment)

		if v.admin_level >=4: items=items.options(joinedload(Comment.oauth_app))

		x=items.filter(Comment.id == i).first()

		if not x and not graceful: abort(404)

		block = g.db.query(UserBlock).filter(
			or_(
				and_(
					UserBlock.user_id == v.id,
					UserBlock.target_id == x.author_id
				),
				and_(UserBlock.user_id == x.author_id,
					 UserBlock.target_id == v.id
					 )
			)
		).first()

		x._is_blocking = block and block.user_id == v.id
		x._is_blocked = block and block.target_id == v.id

	else:
		x = g.db.query(Comment).filter(Comment.id == i).first()
		if not x and not graceful:abort(404)

	return x


def get_comments(cids, v=None):

	if not cids: return []

	cids=tuple(cids)

	output = g.db.query(Comment)

	if v and v.admin_level >=4: output=output.options(joinedload(Comment.oauth_app))

	output = output.options(joinedload(Comment.parent_comment)).filter(Comment.id.in_(cids)).all()

	output = sorted(output, key=lambda x: cids.index(x.id))

	return output


def get_domain(s):

	# parse domain into all possible subdomains
	parts = s.split(".")
	domain_list = set([])
	for i in range(len(parts)):
		new_domain = parts[i]
		for j in range(i + 1, len(parts)):
			new_domain += "." + parts[j]

		domain_list.add(new_domain)

	domain_list = tuple(list(domain_list))

	doms = [x for x in g.db.query(BannedDomain).filter(
		BannedDomain.domain.in_(domain_list)).all()]

	if not doms:
		return None

	# return the most specific domain - the one with the longest domain
	# property
	doms = sorted(doms, key=lambda x: len(x.domain), reverse=True)

	return doms[0]