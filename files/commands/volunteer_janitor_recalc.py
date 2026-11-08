
import sqlalchemy
from sqlalchemy.orm import Session

from collections import defaultdict
from files.classes import User, Comment, UserNote, UserTag
from files.classes.cron.tasks import TaskRunContext
from files.classes.volunteer_janitor import VolunteerJanitorRecord, VolunteerJanitorResult
from files.helpers.volunteer_janitor import RECORD_ORDER, comment_badness, counted_ratings, evaluate_badness_of, userweight_from_user_accuracy, badness_estimate, update_comment_badness
from files.helpers.math import saturate, remap, lerp

import logging

from files.__main__ import app, db_session

CONFIG_modhat_weight = 4
CONFIG_admin_volunteer_weight = 4
CONFIG_new_user_damping = 2
CONFIG_default_user_accuracy = 0.2
CONFIG_user_correctness_lerp = 0.2

def _compile_records(db):
    '''The counted ratings, as {(volunteer, comment): rating}, leaving out comments their author deleted; and every volunteer who stored a rating.'''
    vrecords = db.query(VolunteerJanitorRecord).order_by(*RECORD_ORDER).all()
    raters = {record.user_id for record in vrecords if record.result != VolunteerJanitorResult.Pending}

    # we're just going to ignore deleted comments entirely
    deleted = {row.id for row in db.query(Comment.id).where(Comment.id.in_({record.comment_id for record in vrecords}), Comment.state_user_deleted_utc != None)}

    return {key: record.result for key, record in counted_ratings(vrecords).items() if key[1] not in deleted}, raters

# Calculates how correct a user is, based on whether they thought it was bad, how confident they were, and how bad we think it is
# Returns (IsCorrect, Confidence)
def evaluate_correctness_single(bad, user_weight, calculated_badness):
    # Boolean for whether this comment is bad
    calculated_badbool = calculated_badness > 0.5

    # Boolean for whether the user was correct
    correctness_result = (bad == calculated_badbool) and 1 or 0

    # "how confident are we that this is bad/notbad", range [0, 0.5]
    calculated_badness_confidence = abs(calculated_badness - 0.5)

    # "how much do we want this to influence the user's correctness"
    # there's a deadzone around not-confident where we just push it to 0 and don't make it relevant
    calculated_badness_weight = saturate(remap(calculated_badness_confidence, 0.1, 0.5, 0, 1))

    # see how correct we think the user is
    user_correctness = user_weight * calculated_badness_weight
    
    return correctness_result, user_correctness

def volunteer_janitor_recalc(db: Session) -> tuple[int, int]:
    '''Recalculates every volunteer's accuracy from their ratings, then the badness of the comments they rated; returns how many volunteers it recalculated and how many comments' badness changed.'''
    logging.info("Starting full janitor recalculation")

    # Get our full list of data
    records_compiled, reporting_user_ids = _compile_records(db)

    reported_comment_ids = {record[1] for record in records_compiled}

    # Get some metadata for all reported comments
    comments = db.query(Comment) \
        .where(Comment.id.in_(reported_comment_ids)) \
        .options(sqlalchemy.orm.load_only(Comment.id, Comment.created_utc, Comment.author_id))
    comments = {comment.id: comment for comment in comments}

    reported_user_ids = {comment.author_id for comment in comments.values()}

    # Get mod intervention data
    modhats_raw = db.query(Comment) \
        .where(Comment.parent_comment_id.in_(reported_comment_ids)) \
        .where(Comment.distinguish_level > 0) \
        .options(sqlalchemy.orm.load_only(Comment.parent_comment_id, Comment.created_utc))

    modhat_times = defaultdict(list)
    for modhat in modhats_raw:
        modhat_times[modhat.parent_comment_id].append(modhat.created_utc)

    usernotes_raw = db.query(UserNote) \
        .where(UserNote.reference_user.in_(reported_user_ids)) \
        .where(UserNote.tag.in_([UserTag.Warning, UserTag.Tempban, UserTag.Permban, UserTag.Spam, UserTag.Bot])) \
        .options(sqlalchemy.orm.load_only(UserNote.reference_user, UserNote.created_datetimez, UserNote.tag))
    usernote_times = defaultdict(list)
    for usernote in usernotes_raw:
        usernote_times[usernote.reference_user].append(usernote.created_utc)

    # Here we're trying to figure out whether modhats are actually warnings/bans
    # We don't have a formal connection between "a comment is bad" and "the user got a warning", so we're kind of awkwardly trying to derive it from our database
    # In addition, sometimes someone posts a lot of bad comments and only gets modhatted for one of them
    # That doesn't mean the other comments weren't bad
    # It just means we picked the worst one
    # So we ignore comments near the actual modhat time

    commentresults = {}
    for comment in comments.values():
        note_times = usernote_times[comment.author_id]

        # if the comment was modhatted *and* resulted in a negative usernote near the modhat time, it's bad
        if any(abs(modhat_time - time) < 60 * 15 for modhat_time in modhat_times[comment.id] for time in note_times):
            commentresults[comment.id] = "bad"
        # otherwise, if the comment was posted less than 48 hours before a negative usernote, we ignore it for processing on the assumption that it may just have been part of a larger warning
        elif next((time for time in note_times if comment.created_utc < time and comment.created_utc + 48 * 60 * 60 > time), None) is not None:
            commentresults[comment.id] = "ignored"
        # otherwise, we call it not-bad
        else:
            commentresults[comment.id] = "notbad"

    # get per-user metadata
    users = db.query(User) \
        .where(User.id.in_(reporting_user_ids)) \
        .options(sqlalchemy.orm.load_only(User.id, User.admin_level, User.shadowbanned))
    users = {user.id: {"admin": user.admin_level != 0, "shadowbanned": bool(user.shadowbanned)} for user in users}

    user_accuracy = defaultdict(lambda: CONFIG_default_user_accuracy)
    
    # Do an update loop!
    for lid in range(0, 100):

        # Accumulated weight/badness, taking admin flags into account
        # This is used for training
        comment_weight_admin = defaultdict(lambda: 0)
        comment_badness_admin = defaultdict(lambda: 0)

        # accumulate modhat weights
        for cid in reported_comment_ids:
            result = commentresults[cid]

            if result == "ignored":
                # I guess we'll just let the users decide?
                continue

            if result == "bad":
                comment_weight_admin[cid] += CONFIG_modhat_weight
                comment_badness_admin[cid] += CONFIG_modhat_weight
            
            if result == "notbad":
                comment_weight_admin[cid] += CONFIG_modhat_weight
        
        # accumulate volunteer weights
        for key, value in records_compiled.items():
            uid, cid = key

            # Ratings by shadowbanned volunteers count for nothing, as in a comment's badness
            if users[uid]["shadowbanned"]:
                continue

            # Calculate how much to weight a user; highly inaccurate users are not inverted! They just don't get contribution
            # (losers)
            userweight_user = userweight_from_user_accuracy(user_accuracy[uid]);
            
            if users[uid]["admin"]:
                userweight_admin = CONFIG_admin_volunteer_weight
            else:
                userweight_admin = userweight_user

            bad, weight = evaluate_badness_of(value)

            # Accumulate these to our buffers
            comment_weight_admin[cid] += userweight_admin * weight
            
            if bad:
                comment_badness_admin[cid] += userweight_admin * weight

        # Estimate each comment's badness from the verdicts and the ratings, admins at their fixed weight
        comment_calculated_badness_admin = {cid: badness_estimate(comment_badness_admin[cid], comment_weight_admin[cid]) for cid in reported_comment_ids}

        # go through user submissions and count up how good users seem to be at this
        user_correctness_weight = defaultdict(lambda: CONFIG_new_user_damping)
        user_correctness_value = defaultdict(lambda: CONFIG_default_user_accuracy * CONFIG_new_user_damping)

        for key, value in records_compiled.items():
            uid, cid = key

            # if this is "ignored", I don't trust that we have a real answer, so we just skip it for training purposes
            if commentresults[cid] == "ignored":
                continue

            bad, weight = evaluate_badness_of(value)

            correctness, weight = evaluate_correctness_single(bad, weight, comment_calculated_badness_admin[cid])

            user_correctness_weight[uid] += weight
            user_correctness_value[uid] += correctness * weight

        # calculate new correctnesses
        for uid in reporting_user_ids:
            target_user_correctness = user_correctness_value[uid] / user_correctness_weight[uid]

            # lerp slowly to the new values
            user_accuracy[uid] = lerp(user_accuracy[uid], target_user_correctness, CONFIG_user_correctness_lerp)

    # Shove all this in the database, yaaay
    # Conditional needed because sqlalchemy breaks if you try passing it zero data
    if len(user_accuracy) > 0:
        # In id order, as shadowbans lock users: locked in whatever order the update found them, the two could deadlock
        db.execute(sqlalchemy.text("SELECT id FROM users WHERE id = ANY(:ids) ORDER BY id FOR NO KEY UPDATE"), {"ids": sorted(user_accuracy)})
        db.query(User) \
            .where(User.id.in_([id for id in user_accuracy.keys()])) \
            .update({
                User.volunteer_janitor_correctness: sqlalchemy.sql.case(
                    user_accuracy,
                    value = User.id,
                )
            })
        db.commit()

    comments_changed = _recalc_badness(db)

    logging.info("Finished full janitor recalculation")
    return len(user_accuracy), comments_changed


def _recalc_badness(db: Session) -> int:
    '''Recalculates the badness of every comment volunteers rated, with their accuracies as now stored; returns how many changed.'''
    records = db.query(VolunteerJanitorRecord).options(sqlalchemy.orm.selectinload(VolunteerJanitorRecord.user)).order_by(*RECORD_ORDER).all()
    by_comment = defaultdict(list)
    for record in records:
        by_comment[record.comment_id].append(record)
    rated = sorted(cid for cid, comment_records in by_comment.items() if any(r.result != VolunteerJanitorResult.Pending for r in comment_records))
    stored = dict(db.query(Comment.id, Comment.volunteer_janitor_badness).where(Comment.id.in_(rated)).all())

    # Only the comments whose badness changes take the comment's lock and recount, one at a time, each committed at once so a rating waits for one comment at most
    changed = [cid for cid in rated if comment_badness(by_comment[cid]) != stored[cid]]
    for cid in changed:
        update_comment_badness(db, cid)
        db.commit()
    return len(changed)


@app.cli.command('volunteer_janitor_recalc')
def volunteer_janitor_recalc_cmd():
    volunteers, comments = volunteer_janitor_recalc(db_session())
    print(f"Recalculated the accuracy of {volunteers} volunteers; the badness of {comments} comments changed")

def volunteer_janitor_recalc_cron(ctx:TaskRunContext):
    volunteer_janitor_recalc(ctx.db)
