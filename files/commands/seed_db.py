import hashlib
import math
from typing import Optional
import sqlalchemy
from sqlalchemy.orm import scoped_session

from werkzeug.security import generate_password_hash

from files.__main__ import app, db_session
from files.classes import User, Submission, Comment, Vote, CommentVote
from files.helpers.comments import bulk_recompute_descendant_counts

@app.cli.command('seed_db')
def seed_db():
	seed_db_worker()

def seed_db_worker(num_users = 900, num_posts = 40, num_toplevel_comments = 1000, num_reply_comments = 400):
	"""
	Seed the database with some example data.
	"""
	POST_UPVOTE_PROB      = 0.020
	POST_DOWNVOTE_PROB    = 0.005
	COMMENT_UPVOTE_PROB   = 0.0008
	COMMENT_DOWNVOTE_PROB = 0.0003

	db: scoped_session = db_session() # type: ignore

	def detrand():
		detrand.randstate = bytes(hashlib.sha256(detrand.randstate).hexdigest(), 'utf-8')
		return int(detrand.randstate, 16) / 2**256

	detrand.randstate = bytes(hashlib.sha256(b'init').hexdigest(), 'utf-8')

	users = db.query(User).where(User.id >= 10).all()
	posts = db.query(Submission).all()
	comments = db.query(Comment).all()

	admin = db.query(User).filter(User.id == 9).first()
	if admin is None:
		admin = User(**{
			"username": "admin",
			"original_username": "admin",
			"admin_level": 3,
			"password":"themotteadmin",
			"email":None,
			"ban_evade":0,
			"profileurl":"/e/feather.webp"
		})
		db.add(admin)

	class UserWithFastPasswordHash(User):
		def hash_password(self, password):
			# equivalent to salting and storing a single round of sha512.
			# Not best practice at all for prod but these are test users and we don't care.
			return generate_password_hash(
					password,
					method='pbkdf2:sha512:1',
					salt_length=8
			)

	print(f"Creating {num_users} users")
	users_by_id: dict[int, Optional[User]] = {user_id: None for user_id in range(10, 10 + num_users)}
	for user_id, user in users_by_id.items():
		user = db.query(User).filter(User.id == user_id).first()
		if user is None:
			user = UserWithFastPasswordHash(**{
				"username": f"user{user_id:03d}",
				"original_username": f"user{user_id:03d}",
				"admin_level": 0,
				"password":"themotteuser",
				"email":None,
				"ban_evade":0,
				"profileurl":"/e/feather.webp"
			})
			db.add(user)
		users_by_id[user_id] = user

	db.commit()
	db.flush()

	users = list(users_by_id.values())

	db.commit()
	db.flush()

	posts = []

	print(f"Creating {num_posts} posts")
# 40 top-level posts
	for i in range(num_posts):
		user = users[int(len(users) * detrand())]
		post = Submission(
			private=False,
			club=None,
			author_id=user.id,
			over_18=False,
			app_id=None,
			is_bot=False,
			url=None,
			body=f'This is a post by {user.username}',
			body_html=f'This is a post by {user.username}',
			embed_url=None,
			title=f'Clever unique post title number {i}',
			title_html=f'Clever unique post title number {i}',
			sub=None,
			ghost=False,
			filter_state='normal'
		)
		db.add(post)
		posts.append(post)

	db.commit()

	print(f"Creating {num_toplevel_comments} top-level comments")
	comments = []
# 2k top-level comments, distributed by power-law
	for i in range(num_toplevel_comments):
		user = users[int(len(users) * detrand())]
		parent = posts[int(-math.log(detrand()) / math.log(1.4))]
		comment = Comment(
			author_id=user.id,
			parent_submission=str(parent.id),
			parent_comment_id=None,
			level=1,
			over_18=False,
			is_bot=False,
			app_id=None,
			body_html=f'toplevel {i}',
			body=f'toplevel {i}',
			ghost=False
		)
		db.add(comment)
		comments.append(comment)

	db.flush()
	for c in comments:
		c.top_comment_id = c.id
		db.add(c)

	db.commit()

	print(f"Creating {num_reply_comments} reply comments")
	for i in range(num_reply_comments):
		user = users[int(len(users) * detrand())]
		parent = comments[int(len(comments) * detrand())]
		if parent.id is None:
			db.commit()
		comment = Comment(
			author_id=user.id,
			parent_submission=str(parent.post.id),
			parent_comment_id=parent.id,
			top_comment_id=parent.top_comment_id,
			level=parent.level + 1,
			over_18=False,
			is_bot=False,
			app_id=None,
			body_html=f'reply {i}',
			body=f'reply {i}',
			ghost=False
		)
		db.add(comment)
		comments.append(comment)

	db.commit()

	print("Updating comment counts for all posts")
	for post in posts:
		post.comment_count = len(post.comments)
		db.merge(post)

	print("Adding upvotes and downvotes to posts")
	postvotes = db.query(Vote).all()
	postvotes_pk_set = set((v.submission_id, v.user_id) for v in postvotes)

	for user in users:
		for post in posts:
			if (post.id, user.id) in postvotes_pk_set:
				continue
			r = detrand()
			vote_type = 0
			if post.author_id == user.id:
				vote_type = +1
			elif r < POST_UPVOTE_PROB:
				vote_type = +1
			elif r + POST_DOWNVOTE_PROB > 1:
				vote_type = -1
			if vote_type != 0:
				vote = Vote(
					user_id=user.id,
					vote_type=vote_type,
					submission_id=post.id,
					app_id=None,
					real=True
				)
				db.add(vote)

	print("Adding upvotes and downvotes to comments")
	commentvotes = db.query(CommentVote).all()
	commentvotes_pk_set = set((v.comment_id, v.user_id) for v in commentvotes)

	for user in users:
		for comment in comments:
			if (comment.id, user.id) in commentvotes_pk_set:
				continue
			r = detrand()
			vote_type = 0
			if comment.author_id == user.id:
				vote_type = +1
			elif r < COMMENT_UPVOTE_PROB:
				vote_type = +1
			elif r + COMMENT_DOWNVOTE_PROB > 1:
				vote_type = -1
			if vote_type != 0:
				vote = CommentVote(
					user_id=user.id,
					vote_type=vote_type,
					comment_id=comment.id,
					app_id=None,
					real=True
				)
				db.add(vote)

	db.commit()

	post_upvote_counts = dict(
		db
			.query(Vote.submission_id, sqlalchemy.func.count(1))
			.filter(Vote.vote_type == +1)
			.group_by(Vote.submission_id)
			.all()
	)
	post_downvote_counts = dict(
		db
			.query(Vote.submission_id, sqlalchemy.func.count(1))
			.filter(Vote.vote_type == -1)
			.group_by(Vote.submission_id)
			.all()
	)
	comment_upvote_counts = dict(
		db
			.query(CommentVote.comment_id, sqlalchemy.func.count(1))
			.filter(CommentVote.vote_type == +1)
			.group_by(CommentVote.comment_id)
			.all()
	)
	comment_downvote_counts = dict(
		db
			.query(CommentVote.comment_id, sqlalchemy.func.count(1))
			.filter(CommentVote.vote_type == -1)
			.group_by(CommentVote.comment_id)
			.all()
	)

	for post in posts:
		post.upvotes = post_upvote_counts.get(post.id, 0)
		post.downvotes = post_downvote_counts.get(post.id, 0)
		post.realupvotes = post.upvotes - post.downvotes
		db.add(post)

	for comment in comments:
		comment.upvotes = comment_upvote_counts.get(comment.id, 0)
		comment.downvotes = comment_downvote_counts.get(comment.id, 0)
		comment.realupvotes = comment.upvotes - comment.downvotes
		db.add(comment)

	print("Computing comment descendant_count")
	bulk_recompute_descendant_counts(db=db)

	db.commit()
