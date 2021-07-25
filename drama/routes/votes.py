from drama.helpers.wrappers import *
from drama.helpers.get import *
from drama.classes import *
from flask import *
from drama.__main__ import app


@app.route("/votes", methods=["GET"])
@auth_desired
def admin_vote_info_get(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")

	link = request.args.get("link")
	if not link: return render_template("admin/votes.html", v=v)

	ids = re.search("://[^/]+\w+/post/(\w+)/[^/]+(/(\w+))?", link)

	try:
		post_id = ids.group(1)
		comment_id = ids.group(3)
	except: abort(400)

	if comment_id:
		thing = get_comment(int(comment_id), v=v)

	else:
		thing = get_post(int(post_id), v=v)


	if isinstance(thing, Submission):

		ups = g.db.query(Vote
						 ).options(joinedload(Vote.user)
								   ).filter_by(submission_id=thing.id, vote_type=1
											   ).all()

		downs = g.db.query(Vote
						   ).options(joinedload(Vote.user)
									 ).filter_by(submission_id=thing.id, vote_type=-1
												 ).all()

	elif isinstance(thing, Comment):

		ups = g.db.query(CommentVote
						 ).options(joinedload(CommentVote.user)
								   ).filter_by(comment_id=thing.id, vote_type=1
											   ).all()

		downs = g.db.query(CommentVote
						   ).options(joinedload(CommentVote.user)
									 ).filter_by(comment_id=thing.id, vote_type=-1
												 ).all()

	else:
		abort(400)

	return render_template("admin/votes.html",
						   v=v,
						   thing=thing,
						   ups=ups,
						   downs=downs,)



@app.route("/api/v1/vote/post/<post_id>/<x>", methods=["POST"])
@app.route("/api/vote/post/<post_id>/<x>", methods=["POST"])
@is_not_banned
@api("vote")
@validate_formkey
def api_vote_post(post_id, x, v):

	if x not in ["-1", "0", "1"]: abort(400)

	# disallow bots
	if request.headers.get("X-User-Type","") == "Bot": abort(403)

	x = int(x)

	if x==-1:
		count=g.db.query(Vote).filter(
			Vote.user_id.in_(
				tuple(
					[v.id]+[x.id for x in v.alts]
					)
				),
			Vote.created_utc > (int(time.time())-3600), 
			Vote.vote_type==-1
			).count()
		if count >=15 and v.admin_level==0:
			return jsonify({"error": "You're doing that too much. Try again later."}), 403

	post = get_post(post_id)

	# check for existing vote
	existing = g.db.query(Vote).filter_by(user_id=v.id, submission_id=post.id).first()

	if existing:
		existing.change_to(x)
		g.db.add(existing)
	else:
		vote = Vote(user_id=v.id,
					vote_type=x,
					submission_id=base36decode(post_id),
					app_id=v.client.application.id if v.client else None
					)

		g.db.add(vote)

	g.db.flush()
		
	post.upvotes = post.ups
	post.downvotes = post.downs
	g.db.add(post)
	g.db.commit()
	return "", 204

@app.route("/api/v1/vote/comment/<comment_id>/<x>", methods=["POST"])
@app.route("/api/vote/comment/<comment_id>/<x>", methods=["POST"])
@is_not_banned
@api("vote")
@validate_formkey
def api_vote_comment(comment_id, x, v):

	if x not in ["-1", "0", "1"]:
		abort(400)

	# disallow bots
	if request.headers.get("X-User-Type","") == "Bot":
		abort(403)

	x = int(x)

	comment = get_comment(comment_id)

	# check for existing vote
	existing = g.db.query(CommentVote).filter_by(
		user_id=v.id, comment_id=comment.id).first()
	if existing:
		existing.change_to(x)
		g.db.add(existing)
	else:

		vote = CommentVote(user_id=v.id,
						   vote_type=x,
						   comment_id=base36decode(comment_id),
						   creation_ip=request.remote_addr,
						   app_id=v.client.application.id if v.client else None
						   )

		g.db.add(vote)
	try:
		g.db.flush()
	except:
		return jsonify({"error":"Vote already exists."}), 422

	comment.upvotes = comment.ups
	comment.downvotes = comment.downs
	g.db.add(comment)
	return make_response(""), 204
