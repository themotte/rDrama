
from files.classes.comment import Comment
from files.classes.flags import CommentFlag
from files.classes.user import User
from files.routes.volunteer_common import VolunteerDuty
from flask import g
import pprint
import random

class VolunteerDutyJanitor(VolunteerDuty):

    def __init__(self, choices):
        self.choices = choices

    def accept(self) -> None:
        pprint.pprint(self.choices)
        pass

    def embed_template(self) -> str:
        return "volunteer_janitor.html"

def get_duty(u: User) -> VolunteerDutyJanitor:

    # these could probably be combined into one query somehow

    # find reported comments not made by the current user
    reported_comments = g.db.query(Comment) \
        .where(Comment.filter_state == 'reported') \
        .where(Comment.author_id != u.id) \
        .with_entities(Comment.id)

    reported_ids = [reported.id for reported in reported_comments]
    
    # find distinguished children of those reported comments
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

    final_reported = [report.comment_id for report in nonuser_reports]

    if len(final_reported) <= 0:
        return None
    
    return VolunteerDutyJanitor(random.sample(final_reported, k = min(3, len(final_reported))))
