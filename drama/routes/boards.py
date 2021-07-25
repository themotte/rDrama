from drama.helpers.wrappers import *
from drama.helpers.alerts import *
from drama.classes import *
from flask import *
from drama.__main__ import app, limiter, cache

valid_board_regex = re.compile("^[a-zA-Z0-9][a-zA-Z0-9_]{2,24}$")

@app.route("/mod/distinguish_post/<bid>/<pid>", methods=["POST"])
@app.route("/api/v1/distinguish_post/<bid>/<pid>", methods=["POST"])
@auth_required
@api("guildmaster")
def mod_distinguish_post(bid, pid, board, v):

	#print(pid, board, v)

	post = get_post(pid, v=v)

	if not post.board_id==board.id:
		abort(400)

	if post.author_id != v.id:
		abort(403)

	if post.gm_distinguish:
		post.gm_distinguish = 0
	else:
		post.gm_distinguish = board.id
	g.db.add(post)

	ma=ModAction(
		kind="herald_post" if post.gm_distinguish else "unherald_post",
		user_id=v.id,
		target_submission_id=post.id,
		board_id=board.id
		)
	g.db.add(ma)

	return "", 204

@app.route("/mod/invite_mod/<bid>", methods=["POST"])
@auth_required
@validate_formkey
def mod_invite_username(bid, board, v):

	username = request.form.get("username", '').lstrip('@')
	user = get_user(username)
	if not user:
		return jsonify({"error": "That user doesn't exist."}), 404

	if board.has_ban(user):
		return jsonify({"error": f"@{user.username} is exiled from +{board.name} and can't currently become a guildmaster."}), 409
	if not user.can_join_gms:
		return jsonify({"error": f"@{user.username} already leads enough guilds."}), 409

	x = g.db.query(ModRelationship).filter_by(
		user_id=user.id, board_id=board.id).first()

	if x and x.accepted:
		return jsonify({"error": f"@{user.username} is already a mod."}), 409

	if x and not x.invite_rescinded:
		return jsonify({"error": f"@{user.username} has already been invited."}), 409

	if x:

		x.invite_rescinded = False
		g.db.add(x)

	else:
		x = ModRelationship(
			user_id=user.id,
			board_id=board.id,
			accepted=False,
			perm_full=True,
			perm_content=True,
			perm_appearance=True,
			perm_access=True,
			perm_config=True
			)

		text = f"You have been invited to become an admin. You can [click here](/badmins) and accept this invitation. Or, if you weren't expecting this, you can ignore it."
		send_notification(1046, user, text)

		g.db.add(x)

	ma=ModAction(
		kind="invite_mod",
		user_id=v.id,
		target_user_id=user.id,
		board_id=1
		)
	g.db.add(ma)

	return "", 204


@app.route("/mod/<bid>/rescind/<username>", methods=["POST"])
@auth_required
@validate_formkey
def mod_rescind_bid_username(bid, username, board, v):

	user = get_user(username)

	invitation = g.db.query(ModRelationship).filter_by(board_id=board.id,
													   user_id=user.id,
													   accepted=False).first()
	if not invitation:
		abort(404)

	invitation.invite_rescinded = True

	g.db.add(invitation)
	ma=ModAction(
		kind="uninvite_mod",
		user_id=v.id,
		target_user_id=user.id,
		board_id=1
		)
	g.db.add(ma)
	return "", 204


@app.route("/mod/accept/<bid>", methods=["POST"])
@app.route("/api/v1/accept_invite/<bid>", methods=["POST"])
@auth_required
@validate_formkey
@api("guildmaster")
def mod_accept_board(bid, v):

	board = g.db.query(Board).first()

	x = board.has_invite(v)
	if not x:
		abort(404)

	if not v.can_join_gms:
		return jsonify({"error": f"You already lead enough guilds."}), 409
	if board.has_ban(v):
		return jsonify({"error": f"You are exiled from +{board.name} and can't currently become a guildmaster."}), 409
	x.accepted = True
	x.created_utc=int(time.time())
	g.db.add(x)

	ma=ModAction(
		kind="accept_mod_invite",
		user_id=v.id,
		target_user_id=v.id,
		board_id=board.id
		)
	g.db.add(ma)
	
	v.admin_level = 6
	return "", 204

@app.route("/mod/<bid>/step_down", methods=["POST"])
@auth_required
@validate_formkey
def mod_step_down(bid, board, v):


	v_mod = board.has_mod(v)

	if not v_mod:
		abort(404)

	g.db.delete(v_mod)

	ma=ModAction(
		kind="dethrone_self",
		user_id=v.id,
		target_user_id=v.id,
		board_id=board.id
		)
	g.db.add(ma) 
	v.admin_level = 0
	return "", 204



@app.route("/mod/<bid>/remove/<username>", methods=["POST"])
@auth_required
@validate_formkey
def mod_remove_username(bid, username, board, v):

	user = get_user(username)

	u_mod = board.has_mod(user)
	v_mod = board.has_mod(v)

	if not u_mod:
		abort(400)
	elif not v_mod:
		abort(400)

	if not u_mod.board_id==board.id:
		abort(400)

	if not v_mod.board_id==board.id:
		abort(400)

	if v_mod.id > u_mod.id:
		abort(403)

	g.db.delete(u_mod)

	ma=ModAction(
		kind="remove_mod",
		user_id=v.id,
		target_user_id=user.id,
		board_id=board.id
		)
	g.db.add(ma)

	user.admin_level = 0
	return "", 204

@app.route("/badmins", methods=["GET"])
@app.route("/api/vue/mod/mods",  methods=["GET"])
@app.route("/api/v1/mod/mods", methods=["GET"])
@auth_desired
@public("read")
def board_about_mods(v):

	board = g.db.query(Board).first()

	me = (v.admin_level == 6)

	return {
		"html":lambda:render_template("mods.html", v=v, b=board, me=me),
		"api":lambda:jsonify({"data":[x.json for x in board.mods_list]})
		}

@app.route("/log", methods=["GET"])
@app.route("/api/v1/mod_log", methods=["GET"])
@auth_desired
@api("read")
def board_mod_log(v):

	page=int(request.args.get("page",1))

	if v and v.admin_level == 6: actions = g.db.query(ModAction).order_by(ModAction.id.desc()).offset(25 * (page - 1)).limit(26).all()
	else: actions=g.db.query(ModAction).filter(ModAction.kind!="shadowban", ModAction.kind!="unshadowban").order_by(ModAction.id.desc()).offset(25*(page-1)).limit(26).all()
	actions=[i for i in actions]

	next_exists=len(actions)==26
	actions=actions[0:25]

	return {
		"html":lambda:render_template(
			"modlog.html",
			v=v,
			actions=actions,
			next_exists=next_exists,
			page=page
		),
		"api":lambda:jsonify({"data":[x.json for x in actions]})
		}

@app.route("/log/<aid>", methods=["GET"])
@auth_desired
def mod_log_item(aid, v):

	action=g.db.query(ModAction).filter_by(id=base36decode(aid)).first()

	if not action:
		abort(404)

	if request.path != action.permalink:
		return redirect(action.permalink)

	return render_template("modlog.html",
		v=v,
		actions=[action],
		next_exists=False,
		page=1,
		action=action
		)

@app.route("/mod/edit_perms", methods=["POST"])
@auth_required
@validate_formkey
def board_mod_perms_change(boardname, board, v):

	user=get_user(request.form.get("username"))

	v_mod=board.has_mod(v)
	u_mod=board.has_mod_record(user)

	if v_mod.id > u_mod.id:
		return jsonify({"error":"You can't change perms on badmins above you."}), 403

	#print({x:request.form.get(x) for x in request.form})

	u_mod.perm_full		 = bool(request.form.get("perm_full"		 , False))
	u_mod.perm_access	   = bool(request.form.get("perm_access"	   , False))
	u_mod.perm_appearance   = bool(request.form.get("perm_appearance"   , False))
	u_mod.perm_config	   = bool(request.form.get("perm_config"	   , False))
	u_mod.perm_content	  = bool(request.form.get("perm_content"	  , False))

	g.db.add(u_mod)
	g.db.commit()

	ma=ModAction(
		kind="change_perms" if u_mod.accepted else "change_invite",
		user_id=v.id,
		board_id=board.id,
		target_user_id=user.id,
		note=u_mod.permchangelist
	)
	g.db.add(ma)

	return redirect(f"{board.permalink}/mod/mods")