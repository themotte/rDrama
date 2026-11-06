from typing import Type, Union

from files.__main__ import app, limiter
from files.classes.comment import Comment
from files.classes.submission import Submission
from files.classes.user import User
from files.classes.votes import CommentVote, Vote
from files.helpers.get import get_comment, get_post
from files.helpers.wrappers import admin_level_required, is_not_permabanned
from files.routes.importstar import *


@app.get("/votes")
@limiter.exempt
@admin_level_required(3)
def admin_vote_info_get(v):
	link = request.values.get("link")
	if not link: return render_template("votes.html", v=v)

	if "post_" in link: thing = get_post(link.split("post_")[1], v=v)
	elif "comment_" in link: thing = get_comment(link.split("comment_")[1], v=v)
	else: abort(400)

	if thing.ghost: abort(403)

	if isinstance(thing, Submission):
		ups = g.db.query(Vote).filter_by(submission_id=thing.id, vote_type=1).order_by(Vote.created_datetimez).all()

		downs = g.db.query(Vote).filter_by(submission_id=thing.id, vote_type=-1).order_by(Vote.created_datetimez).all()

	else:
		ups = g.db.query(CommentVote).filter_by(comment_id=thing.id, vote_type=1).order_by(CommentVote.created_datetimez).all()

		downs = g.db.query(CommentVote).filter_by(comment_id=thing.id, vote_type=-1 ).order_by(CommentVote.created_datetimez).all()

	return render_template("votes.html",
						   v=v,
						   thing=thing,
						   ups=ups,
						   downs=downs)


def _vote(target:Union[Submission, Comment], vote_cls:Union[Type[Vote], Type[CommentVote]], new:int, v:User):
	'''Sets `v`'s vote on `target` to `new` (1, 0 or -1), moving the author's truescore by the change unless `v` is the author, and recounts the target's votes.'''
	target_key = vote_cls.submission_id if vote_cls is Vote else vote_cls.comment_id
	# Votes on one item take turns, so each reads the vote and the counts the others left
	g.db.query(type(target)).filter_by(id=target.id).populate_existing().with_for_update(key_share=True).one()
	vote = g.db.query(vote_cls).filter(vote_cls.user_id == v.id, target_key == target.id).one_or_none()
	if vote and vote.vote_type == new: return "", 204

	points_matter = v.id != target.author.id
	if not vote:
		vote = vote_cls(user_id=v.id, vote_type=new, **{target_key.key: target.id})
	elif points_matter:
		target.author.truescore -= vote.vote_type
	vote.vote_type = new
	# Permanently suspended users can't vote at all
	vote.real = not v.shadowbanned
	if points_matter:
		target.author.truescore += new
	g.db.add(target.author)
	g.db.add(vote)

	g.db.flush()
	counts = g.db.query(vote_cls).filter(target_key == target.id)
	target.upvotes = counts.filter(vote_cls.vote_type == 1).count()
	target.downvotes = counts.filter(vote_cls.vote_type == -1).count()
	target.realupvotes = counts.filter(vote_cls.vote_type == 1, vote_cls.real == True).count()
	g.db.add(target)
	g.db.commit()
	return "", 204


def _vote_check_request(new:str) -> int:
	'''The vote a request asks for, refusing API clients and anything but 1, 0 and -1.'''
	if request.headers.get("Authorization"): abort(403)
	if new not in ["-1", "0", "1"]: abort(400)
	return int(new)


def _vote_check_target(target:Union[Submission, Comment], v:User):
	'''Refuses votes on what `v` may not vote on: 404 where they can't open it at all, 403 where it's hidden from them or they block its author.'''
	post = target if isinstance(target, Submission) else target.post
	if not post: abort(404) # private messages have no scores
	if post.is_draft_hidden_from(v): abort(404)
	if getattr(target, 'is_blocking', False): abort(403, "Can't vote on things from users you've blocked")
	if not target.visibility_state.is_visible_to(v): abort(403, "You can't vote on this")


@app.post("/vote/post/<post_id>/<new>")
@limiter.limit("5/second;60/minute;600/hour;1000/day")
@is_not_permabanned
def api_vote_post(post_id, new, v):
	new = _vote_check_request(new)
	post = get_post(post_id, v=v)
	_vote_check_target(post, v)
	return _vote(post, Vote, new, v)


@app.post("/vote/comment/<comment_id>/<new>")
@limiter.limit("5/second;60/minute;600/hour;1000/day")
@is_not_permabanned
def api_vote_comment(comment_id, new, v):
	new = _vote_check_request(new)
	comment = get_comment(comment_id, v=v)
	_vote_check_target(comment, v)
	return _vote(comment, CommentVote, new, v)
