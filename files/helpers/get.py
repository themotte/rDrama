from collections import defaultdict
from typing import Callable, Iterable, List, Optional, Type, Union

from flask import g
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Query, selectinload

from files.classes import *
from files.helpers.const import AUTOJANNY_ID
from files.helpers.contentsorting import sort_comment_results


def get_id(
		username:str,
		graceful:bool=False) -> Optional[int]:

	user = g.db.query(User.id).filter(
		or_(
			func.lower(User.username) == username.lower(),
			func.lower(User.original_username) == username.lower()
			)
		).one_or_none()

	if not user:
		if graceful: return None
		abort(404)

	return user[0]


def get_user(
		username:Optional[str],
		v:Optional[User]=None,
		graceful:bool=False,
		include_blocks:bool=False) -> Optional[User]:
	if not username:
		if graceful: return None
		abort(404)

	user = g.db.query(User).filter(
		or_(
			func.lower(User.username) == username.lower(),
			func.lower(User.original_username) == username.lower()
			)
		).one_or_none()

	if not user:
		if graceful: return None
		abort(404)

	if v and include_blocks:
		user = _add_block_props(user, v)

	return user


def get_users(
		usernames:Iterable[str],
		graceful:bool=False) -> List[User]:
	if not usernames: return []
	if not any(usernames):
		if graceful and len(usernames) == 0: return []
		abort(404)
	users = g.db.query(User).filter(
		or_(
			func.lower(User.username).in_([name.lower() for name in usernames]),
			func.lower(User.original_username).in_([name.lower() for name in usernames])
			)
		).all()

	if len(users) != len(usernames) and not graceful:
		abort(404)

	return users


def get_account(
		id:Union[str,int],
		v:Optional[User]=None,
		graceful:bool=False,
		include_blocks:bool=False) -> Optional[User]:
	try:
		id = int(id)
	except:
		if graceful: return None
		abort(404)

	user = g.db.get(User, id)
	if not user:
		if graceful: return None
		abort(404)

	if v and include_blocks:
		user = _add_block_props(user, v)

	return user


def get_post(
		i:Union[str,int],
		v:Optional[User]=None,
		graceful:bool=False) -> Optional[Submission]:
	try: i = int(i)
	except:
		if graceful: return None
		abort(404)

	if v:
		vt = g.db.query(Vote).filter_by(
			user_id=v.id, submission_id=i).subquery()
		blocking = v.blocking.subquery()

		post = g.db.query(
			Submission,
			vt.c.vote_type,
			blocking.c.target_id,
		)

		post = post.filter(Submission.id == i
		).join(
			vt,
			vt.c.submission_id == Submission.id,
			isouter=True
		).join(
			blocking,
			blocking.c.target_id == Submission.author_id,
			isouter=True
		)
		post = post.one_or_none()
		
		if not post:
			if graceful: return None
			else: abort(404)

		x = post[0]
		x.voted = post[1] or 0
		x.is_blocking = post[2] or 0
	else:
		post = g.db.get(Submission, i)
		if not post:
			if graceful: return None
			else: abort(404)
		x = post

	return x


def get_posts(
		pids:Iterable[int],
		v:Optional[User]=None,
		eager:bool=False) -> List[Submission]:
	if not pids: return []

	if v:
		vt = g.db.query(Vote.vote_type, Vote.submission_id).filter(
			Vote.submission_id.in_(pids), 
			Vote.user_id==v.id
			).subquery()

		blocking = v.blocking.subquery()
		blocked = v.blocked.subquery()

		query = g.db.query(
			Submission,
			vt.c.vote_type,
			blocking.c.target_id,
			blocked.c.target_id,
		).filter(
			Submission.id.in_(pids)
		).join(
			vt, vt.c.submission_id == Submission.id, isouter=True
		).join(
			blocking, blocking.c.target_id == Submission.author_id, isouter=True
		).join(
			blocked, blocked.c.user_id == Submission.author_id, isouter=True
		)
	else:
		query = g.db.query(Submission).filter(Submission.id.in_(pids))

	if eager:
		query = query.options(
			selectinload(Submission.author).options(
				selectinload(User.badges),
				selectinload(User.notes),
			),
			selectinload(Submission.reports),
			selectinload(Submission.awards),
		)

	results = query.all()

	if v:
		output = [p[0] for p in results]
		for i in range(len(output)):
			output[i].voted = results[i][1] or 0
			output[i].is_blocking = results[i][2] or 0
			output[i].is_blocked = results[i][3] or 0
	else:
		output = results

	return sorted(output, key=lambda x: pids.index(x.id))


def get_comment(
		i:Union[str,int],
		v:Optional[User]=None,
		graceful:bool=False) -> Optional[Comment]:
	try: i = int(i)
	except:
		if graceful: return None
		abort(404)
	if not i:
		if graceful: return None
		else: abort(404)

	comment = g.db.get(Comment, i)
	if not comment:
		if graceful: return None
		else: abort(404)

	return _add_vote_and_block_props(comment, v, CommentVote)


def get_comments(
		cids:Iterable[int],
		v:Optional[User]=None) -> List[Comment]:
	if not cids: return []

	if v:
		votes = g.db.query(CommentVote).filter_by(user_id=v.id).subquery()

		blocking = v.blocking.subquery()

		blocked = v.blocked.subquery()

		comments = g.db.query(
			Comment,
			votes.c.vote_type,
			blocking.c.target_id,
			blocked.c.target_id,
		).filter(Comment.id.in_(cids))
 
		if not (v and (v.shadowbanned or v.admin_level > 1)):
			comments = comments.join(User, User.id == Comment.author_id) \
				.filter(User.shadowbanned == None)

		comments = comments.join(
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
		).all()

		output = []
		for c in comments:
			comment = c[0]
			comment.voted = c[1] or 0
			comment.is_blocking = c[2] or 0
			comment.is_blocked = c[3] or 0
			output.append(comment)
	else:
		output = g.db.query(Comment) \
			.join(User, User.id == Comment.author_id) \
			.filter(User.shadowbanned == None, Comment.id.in_(cids)) \
			.all()

	return sorted(output, key=lambda x: cids.index(x.id))


# TODO: There is probably some way to unify this with get_comments. However, in
#       the interim, it's a hot path and benefits from having tailored code.
def get_comment_trees_eager(
		query_filter_callable: Callable[[Query], Query],
		sort: str="old",
		v: Optional[User]=None) -> List[Comment]:

	if v:
		votes = g.db.query(CommentVote).filter_by(user_id=v.id).subquery()
		blocking = v.blocking.subquery()
		blocked = v.blocked.subquery()

		query = g.db.query(
			Comment,
			votes.c.vote_type,
			blocking.c.target_id,
			blocked.c.target_id,
		).join(
			votes, votes.c.comment_id==Comment.id, isouter=True
		).join(
			blocking,
			blocking.c.target_id == Comment.author_id,
			isouter=True
		).join(
			blocked,
			blocked.c.user_id == Comment.author_id,
			isouter=True
		)
	else:
		query = g.db.query(Comment)

	query = query_filter_callable(query)
	query = query.options(
		selectinload(Comment.author).options(
			selectinload(User.badges),
			selectinload(User.notes),
		),
		selectinload(Comment.reports).options(
			selectinload(CommentFlag.user),
		),
		selectinload(Comment.awards),
	)
	results = query.all()

	if v:
		comments = [c[0] for c in results]
		for i in range(len(comments)):
			comments[i].voted = results[i][1] or 0
			comments[i].is_blocking = results[i][2] or 0
			comments[i].is_blocked = results[i][3] or 0
	else:
		comments = results

	comments_map = {}
	comments_map_parent = defaultdict(lambda: list())
	for c in comments:
		c.replies2 = []
		comments_map[c.id] = c
		comments_map_parent[c.parent_comment_id].append(c)

	for parent_id in comments_map_parent:
		comments_map_parent[parent_id] = sort_comment_results(
			comments_map_parent[parent_id], sort)
		if parent_id in comments_map:
			comments_map[parent_id].replies2 = comments_map_parent[parent_id]

	return comments, comments_map_parent


# TODO: This function was concisely inlined into posts.py in upstream.
#       Think it involved adding `tldextract` as a dependency.
def get_domain(s:str) -> Optional[BannedDomain]:
	parts = s.split(".")
	domain_list = set()
	for i in range(len(parts)):
		new_domain = parts[i]
		for j in range(i + 1, len(parts)):
			new_domain += "." + parts[j]

		domain_list.add(new_domain)

	doms = g.db.query(BannedDomain) \
		.filter(BannedDomain.domain.in_(domain_list)).all()
	doms = [x for x in doms]

	if not doms:
		return None

	doms = sorted(doms, key=lambda x: len(x.domain), reverse=True)

	return doms[0]


def _add_block_props(
		target:Union[Submission, Comment, User],
		v:Optional[User]):
	if not v: return target
	id = None

	if any(isinstance(target, cls) for cls in [Submission, Comment]):
		id = target.author_id
	elif isinstance(target, User):
		id = target.id
	else:
		raise TypeError("add_block_props only supports non-None "
						"submissions, comments, and users")

	if hasattr(target, 'is_blocking') and hasattr(target, 'is_blocked'):
		return target

	# users can't block or be blocked by themselves or AutoJanny
	if v.id == id or id == AUTOJANNY_ID:
		target.is_blocking = False
		target.is_blocked = False
		return target

	block = g.db.query(UserBlock).filter(
		or_(
			and_(
				UserBlock.user_id == v.id,
				UserBlock.target_id == id
			),
			and_(
				UserBlock.user_id == id,
				UserBlock.target_id == v.id
			)
		)
	).first()
	target.is_blocking = block and block.user_id == v.id
	target.is_blocked = block and block.target_id == v.id
	return target


def _add_vote_props(
		target:Union[Submission, Comment],
		v:Optional[User],
		vote_cls:Union[Type[Vote], Type[CommentVote], None]):
	if hasattr(target, 'voted'): return target

	vt = g.db.query(vote_cls.vote_type).filter_by(user_id=v.id)
	if vote_cls is Vote:
		vt = vt.filter_by(submission_id=target.id)
	elif vote_cls is CommentVote:
		vt = vt.filter_by(comment_id=target.id)
	else:
		vt = None
	if vt: vt = vt.one_or_none()
	target.voted = vt.vote_type if vt else 0
	return target


def _add_vote_and_block_props(
		target:Union[Submission, Comment],
		v:Optional[User],
		vote_cls:Union[Type[Vote], Type[CommentVote], None]):
	if not v: return target
	target = _add_block_props(target, v)
	return _add_vote_props(target, v, vote_cls)
