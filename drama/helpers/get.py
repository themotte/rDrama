from drama.classes import *
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

def get_account(base36id, v=None, graceful=False):


	if isinstance(base36id, str): id = base36decode(base36id)
	else: id = base36id

	user = g.db.query(User
						  ).filter(
		User.id == id
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


def get_post(pid, v=None, graceful=False, **kwargs):

	print('aaa')
	if isinstance(pid, str):
		i = base36decode(pid)
	else:
		i = pid
	print('bbb')

	if v:
		print('ccc')
		vt = g.db.query(Vote).filter_by(
			user_id=v.id, submission_id=i).subquery()
		blocking = v.blocking.subquery()
		print('ddd')

		items = g.db.query(
			Submission,
			vt.c.vote_type,
			blocking.c.id,
		)
		print('eee')

		if v.admin_level>=4:
			items=items.options(joinedload(Submission.oauth_app))
		print('fff')
		print(i)
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

		print(items.all())
		items=items.first()
		print('ggg')

		if not items and not graceful:
			abort(404)
		print('sexcuse me')
		x = items[0]
		x._voted = items[1] or 0
		x._is_blocking = items[2] or 0
		print("what")
	else:
		items = g.db.query(
			Submission
		).filter(Submission.id == i).first()

		print('help')
		if not items and not graceful:
			abort(404)
		print('me')
		x=items

	print('end of file')
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

def get_comment(cid, v=None, graceful=False, **kwargs):

	if isinstance(cid, str):
		i = base36decode(cid)
	else:
		i = cid

	if v:
		blocking = v.blocking.subquery()
		blocked = v.blocked.subquery()
		vt = g.db.query(CommentVote).filter(
			CommentVote.user_id == v.id,
			CommentVote.comment_id == i).subquery()

		items = g.db.query(
			Comment, 
			vt.c.vote_type,
		)

		if v.admin_level >=4:
			items=items.options(joinedload(Comment.oauth_app))

		items=items.filter(
			Comment.id == i
		).join(
			vt, 
			vt.c.comment_id == Comment.id, 
			isouter=True
		).join(
			Comment.post,
			isouter=True
		).first()

		if not items and not graceful:
			abort(404)

		x = items[0]
		x._voted = items[1] or 0

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
		x = g.db.query(
			Comment,
		).filter(Comment.id == i).first()

		if not x and not graceful:
			abort(404)


	return x


def get_comments(cids, v=None, load_parent=False, **kwargs):

	if not cids:
		return []

	cids=tuple(cids)

	if v:
		vt = g.db.query(CommentVote).filter(
			CommentVote.comment_id.in_(cids), 
			CommentVote.user_id==v.id
			).subquery()

		query = g.db.query(
			Comment, 
			aliased(CommentVote, alias=vt),
			)

		if v.admin_level >=4:
			query=query.options(joinedload(Comment.oauth_app))

		if load_parent:
			query = query.options(
				joinedload(
					Comment.parent_comment
					)
				)

		query = query.join(
			vt,
			vt.c.comment_id == Comment.id,
			isouter=True
			).join(
			Comment.post,
			isouter=True
			).filter(
			Comment.id.in_(cids)
			)


		output = [x[0] for x in query]
		for i in range(len(output)):
			output[i]._voted = query[i][1].vote_type if query[i][1] else 0


	else:
		query = g.db.query(
			Comment,
		).filter(
			Comment.id.in_(cids)
		).all()

		output=[x for x in query]

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

	doms = [x for x in g.db.query(Domain).filter(
		Domain.domain.in_(domain_list)).all()]

	if not doms:
		return None

	# return the most specific domain - the one with the longest domain
	# property
	doms = sorted(doms, key=lambda x: len(x.domain), reverse=True)

	return doms[0]