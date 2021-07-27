from drama.__main__ import app
from drama.helpers.wrappers import *
from drama.helpers.alerts import *
from drama.helpers.get import *
from drama.classes.award import *
from flask import g, jsonify, request


def banaward_trigger(post=None, comment=None):

    author = post.author if post else comment.author

    if not author.is_suspended or author.admin_level < 1:
        author.ban(reason="1-day ban award used", days=1)

        link = f"[this post]({post.permalink})" if post else f"[this comment]({comment.permalink})"

        send_notification(1046, author, f"Your Drama account has been suspended for a day for {link}. It sucked and you should feel bad.")


ACTIONS = {
    "ban": banaward_trigger
}


@app.get("/api/awards")
@auth_required
def get_awards(v):

    return_value = list(AWARDS.values())

    user_awards = v.awards
    for val in return_value:
        val['owned'] = len([x for x in user_awards if x.kind == val['kind'] and not x.given])

    return jsonify(return_value)


@app.put("/api/post/<pid>/awards")
@auth_required
@validate_formkey
def award_post(pid, v):

    if v.is_suspended and v.unban_utc == 0:
        return jsonify({"error": "forbidden"}), 403

    kind = request.form.get("kind", "")

    if kind not in AWARDS:
        return jsonify({"error": "That award doesn't exist."}), 404

    post_award = g.db.query(AwardRelationship).filter(
        and_(
            AwardRelationship.kind == kind,
            AwardRelationship.user_id == v.id,
            AwardRelationship.submission_id == None,
            AwardRelationship.comment_id == None
        )
    ).first()

    if not post_award:
        return jsonify({"error": "You don't have that award."}), 404

    post = g.db.query(Submission).filter_by(id=pid).first()

    if not post or post.is_banned or post.deleted_utc > 0:
        return jsonify({"error": "That post doesn't exist or has been deleted or removed."}), 404

    if post.author_id == v.id:
        return jsonify({"error": "You can't award yourself."}), 403

    existing_award = g.db.query(AwardRelationship).filter(
        and_(
            AwardRelationship.submission_id == post.id,
            AwardRelationship.user_id == v.id
        )
    ).first()

    if existing_award:
        return jsonify({"error": "You already awarded this post."}), 409

    post_award.submission_id = post.id
    g.db.add(post_award)

    msg = f"Your [post]({post.permalink}) was given the {AWARDS[kind]['title']} Award!"

    note = request.form.get("note", "")
    if note:
        msg += f"\n\n> {note}"

    send_notification(1046, post.author, msg)

    if kind in ACTIONS:
        ACTIONS[kind](post=post)

    return "", 204


@app.put("/api/comment/<cid>/awards")
@auth_required
@validate_formkey
def award_comment(cid, v):

    if v.is_suspended and v.unban_utc == 0:
        return jsonify({"error": "forbidden"}), 403

    kind = request.form.get("kind", "")

    if kind not in AWARDS:
        return jsonify({"error": "That award doesn't exist."}), 404

    comment_award = g.db.query(AwardRelationship).filter(
        and_(
            AwardRelationship.kind == kind,
            AwardRelationship.user_id == v.id,
            AwardRelationship.submission_id == None,
            AwardRelationship.comment_id == None
        )
    ).first()

    if not comment_award:
        return jsonify({"error": "You don't have that award."}), 404

    c = g.db.query(Comment).filter_by(id=cid).first()

    if not c or c.is_banned or c.deleted_utc > 0:
        return jsonify({"error": "That comment doesn't exist or has been deleted or removed."}), 404

    if c.author_id == v.id:
        return jsonify({"error": "You can't award yourself."}), 403

    existing_award = g.db.query(AwardRelationship).filter(
        and_(
            AwardRelationship.comment_id == c.id,
            AwardRelationship.user_id == v.id
        )
    ).first()

    if existing_award:
        return jsonify({"error": "You already awarded this comment."}), 409

    comment_award.comment_id = c.id
    g.db.add(comment_award)

    msg = f"Your [comment]({c.permalink}) was given the {AWARDS[kind]['title']} Award!"

    note = request.form.get("note", "")
    if note:
        msg += f"\n\n> {note}"

    send_notification(1046, c.author, msg)

    if kind in ACTIONS:
        ACTIONS[kind](comment=c)

    return "", 204
