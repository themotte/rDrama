from typing import Optional
from files.__main__ import app
from files.classes.comment import Comment
from files.classes.flags import CommentFlag
from files.classes.submission import Submission
from files.classes.user import User
from files.classes.userblock import UserBlock
from files.classes.visstate import StateReport, StateMod
from files.classes.volunteer_janitor import VolunteerJanitorRecord, VolunteerJanitorResult
from files.helpers.volunteer_janitor import update_comment_badness
from flask import g
import random
import sqlalchemy
from sqlalchemy.orm import aliased


def accept(v: User, choices: list[int]) -> None:
    for item in choices:
        record = VolunteerJanitorRecord()
        record.user_id = v.id
        record.comment_id = item
        record.result = VolunteerJanitorResult.Pending
        g.db.add(record)

    g.db.commit()


def comments(choices: list[int]) -> list[Comment]:
    return g.db.query(Comment).where(Comment.id.in_(choices)).all()


def get_duty(u: User) -> Optional[list[int]]:
    if not app.config['VOLUNTEER_JANITOR_ENABLE']:  # pragma: no cover (a deployment switch, on unless configured off; outside the spec)
        return None

    # these could probably be combined into one query somehow

    # find reported visible comments on posts that aren't drafts, not made by the current user or in reply to the current user, that the current user would see whole, and that carry no moderation outcome
    ParentComment = aliased(Comment)
    reported_comments = g.db.query(Comment) \
        .join(Submission, Submission.id == Comment.parent_submission) \
        .where(Submission.private == False) \
        .where(Comment.state_report == StateReport.REPORTED) \
        .where(Comment.state_mod == StateMod.VISIBLE) \
        .where(Comment.state_user_deleted_utc == None) \
        .where(Comment.author_id != u.id) \
        .where(Comment.distinguish_level == 0, Comment.is_pinned == None, sqlalchemy.not_(sqlalchemy.func.coalesce(Comment.bannedfor, False))) \
        .outerjoin(ParentComment, ParentComment.id == Comment.parent_comment_id) \
        .where(sqlalchemy.or_(ParentComment.author_id != u.id, ParentComment.author_id == None)) \
        .join(User, User.id == Comment.author_id) \
        .where(User.shadowbanned == None) \
        .where(Comment.author_id.notin_(sqlalchemy.select(UserBlock.target_id).where(UserBlock.user_id == u.id))) \
        .where(Comment.author_id.notin_(sqlalchemy.select(UserBlock.user_id).where(UserBlock.target_id == u.id))) \
        .with_entities(Comment.id)
    if not u.over_18:
        reported_comments = reported_comments.where(Comment.over_18 == False, Submission.over_18 == False)

    reported_ids = [reported.id for reported in reported_comments]
    
    if not app.config['DBG_VOLUNTEER_PERMISSIVE']:
        # find distinguished children of those reported comments
        # this is a ghastly query and should be fixed when we're doing some kind of cleanup and mod-action formalization
        distinguished_children = g.db.query(Comment) \
            .where(Comment.parent_comment_id.in_(reported_ids)) \
            .where(Comment.distinguish_level > 0) \
            .with_entities(Comment.parent_comment_id)

        distinguished_children_ids = [child.parent_comment_id for child in distinguished_children]

        # filter
        # we're doing this because we don't want to give people hints as to the "right" result
        # once a modhat hits, that's it, doesn't show up in the volunteer system anymore
        clean_reported = set(reported_ids) - set(distinguished_children_ids)

        # also, let's make sure it has a report that isn't made by this user
        nonuser_reports = g.db.query(CommentFlag) \
            .where(CommentFlag.comment_id.in_(clean_reported)) \
            .where(CommentFlag.user_id != u.id) \
            .with_entities(CommentFlag.comment_id)

        # also, let's make sure it hasn't already been looked at by this user
        seen_records = g.db.query(VolunteerJanitorRecord) \
            .where(VolunteerJanitorRecord.comment_id.in_(nonuser_reports)) \
            .where(VolunteerJanitorRecord.user_id == u.id) \
            .with_entities(VolunteerJanitorRecord.comment_id)

        final_reported = list({report.comment_id for report in nonuser_reports} - {record.comment_id for record in seen_records})
    else:  # pragma: no cover (DBG_VOLUNTEER_PERMISSIVE relaxes the limits for trying duties out in development; outside the spec)
        final_reported = reported_ids

    if len(final_reported) <= 0:
        return None
    
    return random.sample(final_reported, k = min(3, len(final_reported)))

def submitted(v: User, key: str, val: str) -> None:
    record = VolunteerJanitorRecord()
    record.user_id = v.id
    record.comment_id = key
    record.result = VolunteerJanitorResult(int(val))
    g.db.add(record)

    update_comment_badness(g.db, key)

    g.db.commit()
