from typing import Optional
from files.__main__ import app
from files.classes.comment import Comment
from files.classes.flags import CommentFlag
from files.classes.submission import Submission
from files.classes.user import User
from files.classes.userblock import UserBlock
from files.classes.visstate import StateReport, StateMod
from files.classes.volunteer_janitor import VolunteerJanitorRecord, VolunteerJanitorResult
from files.helpers.get import parse_id
from files.helpers.locks import volunteer_duty_lock
from files.helpers.volunteer_janitor import update_comment_badness
from flask import abort, g
import random
import sqlalchemy
from sqlalchemy.orm import aliased


def accept(v: User, choices: list[int]) -> list[VolunteerJanitorRecord]:
    '''Assigns `v` the comments `choices` to rate, answering the assignments.'''
    records = [VolunteerJanitorRecord(user_id=v.id, comment_id=item, result=VolunteerJanitorResult.Pending) for item in choices]
    g.db.add_all(records)
    g.db.flush()
    return records


def assigned_comments(assignments: list[VolunteerJanitorRecord]) -> list[tuple[int, Comment]]:
    '''Each assignment's id with its comment.'''
    comments = {c.id: c for c in g.db.query(Comment).where(Comment.id.in_([a.comment_id for a in assignments]))}
    return [(a.id, comments[a.comment_id]) for a in assignments]


def _still_wanted() -> list:
    '''The conditions under which a comment is one duties are made of, whoever the volunteer: its reports are open, it is visible and not deleted, its author isn't shadowbanned, and the moderators haven't spoken on it (it isn't distinguished, pinned or marked as a ban's reason, and no direct reply to it is distinguished).'''
    Reply = aliased(Comment)
    Author = aliased(User)
    return [
        Comment.state_report == StateReport.REPORTED,
        Comment.state_mod == StateMod.VISIBLE,
        Comment.state_user_deleted_utc == None,
        Comment.distinguish_level == 0,
        Comment.is_pinned == None,
        sqlalchemy.not_(sqlalchemy.func.coalesce(Comment.bannedfor, False)),
        # once a modhat hits, that's it, doesn't show up in the volunteer system anymore: we don't want to give people hints as to the "right" result
        ~sqlalchemy.exists().where(Reply.parent_comment_id == Comment.id, Reply.distinguish_level > 0),
        ~sqlalchemy.exists().where(Author.id == Comment.author_id, Author.shadowbanned != None),
    ]


def get_duty(u: User) -> Optional[list[int]]:
    if not app.config['VOLUNTEER_JANITOR_ENABLE']:  # pragma: no cover (a deployment switch, on unless configured off; outside the spec)
        return None

    # these could probably be combined into one query somehow

    # find reported visible comments on posts that aren't drafts, not made by the current user, in reply to them or on their posts, that the current user would see whole, and that carry no moderation outcome
    ParentComment = aliased(Comment)
    reported_comments = g.db.query(Comment) \
        .join(Submission, Submission.id == Comment.parent_submission) \
        .where(Submission.private == False) \
        .where(*_still_wanted()) \
        .where(Comment.author_id != u.id, Submission.author_id != u.id) \
        .outerjoin(ParentComment, ParentComment.id == Comment.parent_comment_id) \
        .where(sqlalchemy.or_(ParentComment.author_id != u.id, ParentComment.author_id == None)) \
        .where(Comment.author_id.notin_(sqlalchemy.select(UserBlock.target_id).where(UserBlock.user_id == u.id))) \
        .where(Comment.author_id.notin_(sqlalchemy.select(UserBlock.user_id).where(UserBlock.target_id == u.id))) \
        .with_entities(Comment.id)
    if not u.over_18:
        reported_comments = reported_comments.where(Comment.over_18 == False, Submission.over_18 == False)

    reported_ids = [reported.id for reported in reported_comments]
    
    if not app.config['DBG_VOLUNTEER_PERMISSIVE']:
        # let's make sure it has a report that isn't made by this user, by someone whose reports bring items to the moderators
        nonuser_reports = g.db.query(CommentFlag) \
            .where(CommentFlag.comment_id.in_(reported_ids)) \
            .where(CommentFlag.user_id != u.id) \
            .join(User, User.id == CommentFlag.user_id) \
            .where(User.reports_count) \
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

RATINGS = {str(result.value): result for result in VolunteerJanitorResult if result != VolunteerJanitorResult.Pending}


def submitted(v: User, ratings: dict[str, str]) -> None:
    '''Stores `v`'s ratings, given as {assignment id: rating} as the form sends them, of the comments still wanted; the others are left out without a word, so the answer doesn't tell the volunteer what the moderators did. Refuses them all (400) unless each names one of `v`'s assignments, a comment assigned to them and not yet rated by them, and no two name the same comment.'''
    if not ratings: return
    parsed = {parse_id(key): RATINGS.get(value) for key, value in ratings.items()}
    # Two spellings of one id (such as 1 and 01) name it twice
    if None in parsed or None in parsed.values() or len(parsed) != len(ratings): abort(400)

    # Ratings by one volunteer take turns, so each sees what the others stored
    volunteer_duty_lock(g.db, v.id)
    assigned = dict(g.db.query(VolunteerJanitorRecord.id, VolunteerJanitorRecord.comment_id) \
        .where(VolunteerJanitorRecord.id.in_(parsed), VolunteerJanitorRecord.user_id == v.id, VolunteerJanitorRecord.result == VolunteerJanitorResult.Pending) \
        .all())
    by_comment = {assigned.get(aid): result for aid, result in parsed.items()}
    if len(assigned) != len(parsed) or len(by_comment) != len(parsed): abort(400)
    rated = g.db.query(VolunteerJanitorRecord.comment_id) \
        .where(VolunteerJanitorRecord.user_id == v.id, VolunteerJanitorRecord.comment_id.in_(by_comment), VolunteerJanitorRecord.result != VolunteerJanitorResult.Pending) \
        .first()
    if rated: abort(400)
    wanted = {row[0] for row in g.db.query(Comment.id).where(Comment.id.in_(by_comment), *_still_wanted())}

    # In comment id order, as the badness updates lock the comments: ratings of overlapping duties mustn't deadlock
    for cid, result in sorted(by_comment.items()):
        if cid not in wanted: continue
        g.db.add(VolunteerJanitorRecord(user_id=v.id, comment_id=cid, result=result))
        update_comment_badness(g.db, cid)

    g.db.commit()
