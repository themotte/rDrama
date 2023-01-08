
from files.__main__ import app
from files.classes.comment import Comment
from files.classes.flags import CommentFlag
from files.classes.user import User
from files.classes.volunteer_janitor import VolunteerJanitorRecord, VolunteerJanitorResult
from files.routes.volunteer_common import VolunteerDuty
from flask import g
import random
import sqlalchemy

class VolunteerDutyJanitor(VolunteerDuty):

    def __init__(self, choices):
        self.choices = choices

    def accept(self, v) -> None:
        for item in self.choices:
            record = VolunteerJanitorRecord()
            record.user_id = v.id
            record.comment_id = item
            record.recorded_utc = sqlalchemy.func.now()
            record.result = VolunteerJanitorResult.Pending
            g.db.add(record)
        
        g.db.commit()

    def embed_template(self) -> str:
        return "volunteer_janitor.html"
    
    def comments(self) -> list[Comment]:
        return g.db.query(Comment).where(Comment.id.in_(self.choices))


def get_duty(u: User) -> VolunteerDutyJanitor:
    if not app.config['VOLUNTEER_JANITOR_ENABLE']:
        return None

    # these could probably be combined into one query somehow

    # find reported not-deleted comments not made by the current user
    reported_comments = g.db.query(Comment) \
        .where(Comment.filter_state == 'reported') \
        .where(Comment.deleted_utc == 0) \
        .where(Comment.is_approved == None) \
        .where(Comment.author_id != u.id) \
        .with_entities(Comment.id)

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
    else:
        final_reported = reported_ids

    if len(final_reported) <= 0:
        return None
    
    return VolunteerDutyJanitor(random.sample(final_reported, k = min(3, len(final_reported))))

def submitted(v: User, key: str, val: str) -> None:
    record = VolunteerJanitorRecord()
    record.user_id = v.id
    record.comment_id = key
    record.recorded_utc = sqlalchemy.func.now()
    record.result = VolunteerJanitorResult(int(val))
    g.db.add(record)
    g.db.commit()
