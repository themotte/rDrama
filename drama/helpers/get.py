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

	if isinstance(pid, str):
		i = base36decode(pid)
	else:
		i = pid

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
		).first()

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


def get_post_with_comments(pid, sort="top", v=None):

	post = get_post(pid, v=v)

	if v:
		votes = g.db.query(CommentVote).filter_by(user_id=v.id).subquery()

		blocking = v.blocking.subquery()

		blocked = v.blocked.subquery()

		comms = g.db.query(
			Comment,
			votes.c.vote_type,
			blocking.c.id,
			blocked.c.id,
		)
		if v.admin_level >=4:
			comms=comms.options(joinedload(Comment.oauth_app))
 
		comms=comms.filter(
			Comment.parent_submission == post.id
		).join(
			votes,
			votes.c.comment_id == Comment.id,
			isouter=True
		).join(
			blocking,
			blocking.c.target_id == Comment.author_id,
			isouter=True
		).join(
			blocked,
			blocked.c.user_id == Comment.author_id,
			isouter=True
		)

		if sort == "top":
			comments = comms.order_by(Comment.score.desc()).all()
		elif sort == "bottom":
			comments = comms.order_by(Comment.score.asc()).all()
		elif sort == "new":
			comments = comms.order_by(Comment.created_utc.desc()).all()
		elif sort == "old":
			comments = comms.order_by(Comment.created_utc.asc()).all()
		elif sort == "controversial":
			comments = sorted(comms.all(), key=lambda x: x[0].score_disputed, reverse=True)
		elif sort == "random":
			c = comms.all()
			comments = random.sample(c, k=len(c))
		else:
			abort(422)

		output = []
		for c in comments:
			comment = c[0]
			if comment.author and comment.author.shadowbanned and not (v and v.id == comment.author_id): continue
			comment._voted = c[1] or 0
			comment._is_blocking = c[2] or 0
			comment._is_blocked = c[3] or 0
			output.append(comment)

		post._preloaded_comments = output

	else:
		comms = g.db.query(
			Comment
		).filter(
			Comment.parent_submission == post.id
		)

		if sort == "top":
			comments = comms.order_by(Comment.score.desc()).all()
		elif sort == "bottom":
			comments = comms.order_by(Comment.score.asc()).all()
		elif sort == "new":
			comments = comms.order_by(Comment.created_utc.desc()).all()
		elif sort == "old":
			comments = comms.order_by(Comment.created_utc.asc()).all()
		elif sort == "controversial":
			comments = sorted(comms.all(), key=lambda x: x.score_disputed, reverse=True)
		elif sort == "random":
			c = comms.all()
			comments = random.sample(c, k=len(c))
		else:
			abort(422)

		if random.random() < 0.1:
			for comment in comments:
				if comment.author and comment.author.shadowbanned:
					rand = random.randint(500,1400)
					vote = CommentVote(user_id=rand,
						vote_type=random.choice([-1, 1]),
						comment_id=comment.id)
					g.db.add(vote)
					try: g.db.flush()
					except: g.db.rollback()
					comment.upvotes = comment.ups
					comment.downvotes = comment.downs
					g.db.add(comment)

		post._preloaded_comments = [x for x in comments if not (x.author and x.author.shadowbanned) or (v and v.id == x.author_id)]

	return post


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


def get_board(bid, graceful=False):

	return g.db.query(Board).first()


def get_guild(name, graceful=False):

	return g.db.query(Board).first()


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


def get_application(client_id, graceful=False):

	application = g.db.query(OauthApp).filter_by(client_id=client_id).first()
	if not application and not graceful:
		abort(404)

	return application


def get_from_permalink(link, v=None):

	if "@" in link:

		name = re.search("/@(\w+)", link)
		if name:
			name=name.match(1)
			return get_user(name)

	if "+" in link:

		x = re.search("/\+(\w+)$", link)
		if x:
			name=x.match(1)
			return get_guild(name)

	ids = re.search("://[^/]+\w+/post/(\w+)/[^/]+(/(\w+))?", link)

	try:
		post_id = ids.group(1)
		comment_id = ids.group(3)
	except: abort(400)

	if comment_id:
		return get_comment(int(comment_id), v=v)

	else:
		return get_post(int(post_id), v=v)