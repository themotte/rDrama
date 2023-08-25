
import pprint

import sqlalchemy
from sqlalchemy.orm import Session

from alive_progress import alive_it
from collections import defaultdict
from files.classes import User, Comment, UserNote, UserTag
from files.classes.cron.tasks import TaskRunContext
from files.classes.volunteer_janitor import VolunteerJanitorRecord, VolunteerJanitorResult
from files.helpers.volunteer_janitor import evaluate_badness_of, userweight_from_user_accuracy, calculate_final_comment_badness, update_comment_badness
from files.helpers.math import saturate, remap, lerp

import logging
import random

from files.__main__ import app, db_session

CONFIG_modhat_weight = 4
CONFIG_admin_volunteer_weight = 4
CONFIG_new_user_damping = 2
CONFIG_default_user_accuracy = 0.2
CONFIG_user_correctness_lerp = 0.2

def _compile_records(db):
    vrecords = db.query(VolunteerJanitorRecord).order_by(VolunteerJanitorRecord.recorded_datetimez).all()

    # get the info we need for all mentioned posts
    reported_comment_ids = {record.comment_id for record in vrecords}
    reported_comments = db.query(Comment).where(Comment.id.in_(reported_comment_ids)).options(sqlalchemy.orm.load_only('id', 'state_user_deleted_utc'))
    reported_comments = {comment.id: comment for comment in reported_comments}

    # get our compiled data
    records_compiled = {}
    for record in vrecords:
        # we're just going to ignore deleted comments entirely
        if reported_comments[record.comment_id].state_user_deleted_utc != None:
            continue

        # unique identifier for user/comment report pair
        uic = (record.user_id, record.comment_id)

        if record.result == VolunteerJanitorResult.Pending:
            if uic in records_compiled:
                # something wonky happened, we went back to pending after getting a result?
                records_compiled[uic]["status"] = "wonky"
            else:
                # fill out the pending field
                records_compiled[uic] = {"status": "pending"}
        else:
            if not uic in records_compiled:
                # something wonky happened, we never asked them for the info to begin with
                records_compiled[uic] = {"status": "wonky"}
            elif records_compiled[uic]["status"] != "pending":
                # received two submissions; practically we'll just use their first submission
                records_compiled[uic]["status"] = "resubmit"
            else:
                # actually got a result, yay
                records_compiled[uic]["status"] = "submit"
                records_compiled[uic]["result"] = record.result

    # todo:
    # filter out anything submitted *after* a mod chimed in
    # filter out anything submitted too long after the request

    users_compiled = defaultdict(lambda: {
                "pending": 0,
                "wonky": 0,
                "submit": 0,
                "resubmit": 0,
            })
    for key, result in records_compiled.items():
        #pprint.pprint(key)
        userid = key[0]
        
        users_compiled[key[0]][result["status"]] += 1

    #pprint.pprint(records_compiled)
    #pprint.pprint(users_compiled)

    # strip out invalid records
    random_removal = -1 # this is sometimes useful for testing that our algorithm is somewhat stable; removing a random half of all responses shouldn't drastically invert people's quality scores, for example
    records_compiled = {key: value for key, value in records_compiled.items() if "result" in value and random.random() > random_removal}

    return records_compiled, users_compiled

def dbg_commentdump(cid, records_compiled, users, user_accuracy):
    print(f"Dump for comment {cid}")

    from tabulate import tabulate

    dats = []
    for key, value in [(key, value) for key, value in records_compiled.items() if key[1] == cid]:
        uid = key[0]
        dats.append({
            "vote": value["result"],
            "username": users[uid]["username"],
            "accuracy": user_accuracy[uid],
        })
    print(tabulate(dats, headers = "keys"))

def dbg_userdump(uid, records_compiled, users, comment_calculated_badness_user):
    print(f"Dump for user {users[uid]['username']}")

    from tabulate import tabulate

    dats = []
    for key, value in [(key, value) for key, value in records_compiled.items() if key[0] == uid]:
        cid = key[1]
        bad, weight = evaluate_badness_of(value["result"])
        dats.append({
            "cid": cid,
            "vote": value["result"],
            "calculated": evaluate_badness_of(value["result"]),
            "badness": comment_calculated_badness_user[cid],
            "correctness": evaluate_correctness_single(bad, weight, comment_calculated_badness_user[cid]),
        })
    print(tabulate(dats, headers = "keys"))

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

def volunteer_janitor_recalc(db: Session, diagnostics: bool = False):
    logging.info("Starting full janitor recalculation")

    # Get our full list of data
    records_compiled, users_compiled = _compile_records(db)

    reporting_user_ids = {record[0] for record in records_compiled}
    reported_comment_ids = {record[1] for record in records_compiled}

    # Get some metadata for all reported comments
    comments = db.query(Comment) \
        .where(Comment.id.in_(reported_comment_ids)) \
        .options(sqlalchemy.orm.load_only('id', 'created_utc', 'author_id'))
    comments = {comment.id: comment for comment in comments}

    reported_user_ids = {comment.author_id for comment in comments.values()}

    # Get mod intervention data
    modhats_raw = db.query(Comment) \
        .where(Comment.parent_comment_id.in_(reported_comment_ids)) \
        .where(Comment.distinguish_level > 0) \
        .options(sqlalchemy.orm.load_only('parent_comment_id', 'created_utc'))

    modhats = {}
    # we jump through some hoops to deduplicate this; I guess we just pick the last one in our list for now
    for modhat in modhats_raw:
        modhats[modhat.parent_comment_id] = modhat

    usernotes_raw = db.query(UserNote) \
        .where(UserNote.tag.in_([UserTag.Warning, UserTag.Tempban, UserTag.Permban, UserTag.Spam, UserTag.Bot])) \
        .options(sqlalchemy.orm.load_only('reference_user', 'created_datetimez', 'tag'))

    # Here we're trying to figure out whether modhats are actually warnings/bans
    # We don't have a formal connection between "a comment is bad" and "the user got a warning", so we're kind of awkwardly trying to derive it from our database
    # In addition, sometimes someone posts a lot of bad comments and only gets modhatted for one of them
    # That doesn't mean the other comments weren't bad
    # It just means we picked the worst one
    # So we ignore comments near the actual modhat time

    commentresults = {}
    for uid in reported_user_ids:
        # For each user, figure out when modhats happened
        # this is slow but whatever
        modhat_times = []
        for modhat in modhats.values():
            if comments[modhat.parent_comment_id].author_id != uid:
                continue
            
            modhat_times.append(modhat.created_utc)
        
        usernote_times = []
        for usernote in usernotes_raw:
            if usernote.reference_user != uid:
                continue
            
            usernote_times.append(usernote.created_utc)
        
        # For each comment . . .
        for comment in comments.values():
            if comment.author_id != uid:
                continue

            if comment.id in modhats:
                modhat_comment = modhats[comment.id]
            else:
                modhat_comment = None

            # if the comment was modhatted *and* resulted in a negative usernote near the modhat time, it's bad
            if modhat_comment is not None and next((time for time in usernote_times if abs(modhat_comment.created_utc - time) < 60 * 15), None) is not None:
                commentresults[comment.id] = "bad"
            # otherwise, if the comment was posted less than 48 hours before a negative usernote, we ignore it for processing on the assumption that it may just have been part of a larger warning
            elif next((time for time in usernote_times if comment.created_utc < time and comment.created_utc + 48 * 60 * 60 > time), None) is not None:
                commentresults[comment.id] = "ignored"
            # otherwise, we call it not-bad
            else:
                commentresults[comment.id] = "notbad"

    # get per-user metadata
    users = db.query(User) \
        .where(User.id.in_(reporting_user_ids)) \
        .options(sqlalchemy.orm.load_only('id', 'username', 'admin_level'))
    users = {user.id: {"username": user.username, "admin": user.admin_level != 0} for user in users}

    user_accuracy = defaultdict(lambda: CONFIG_default_user_accuracy)
    
    # Do an update loop!
    for lid in range(0, 100):

        # Accumulated weight/badness, taking admin flags into account
        # This is used for training
        comment_weight_admin = defaultdict(lambda: 0)
        comment_badness_admin = defaultdict(lambda: 0)

        # Accumulated weight/badness, not taking admin flags into account
        # This is used for output and display
        comment_weight_user = defaultdict(lambda: 0)
        comment_badness_user = defaultdict(lambda: 0)

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

            # Calculate how much to weight a user; highly inaccurate users are not inverted! They just don't get contribution
            # (losers)
            userweight_user = userweight_from_user_accuracy(user_accuracy[uid]);
            
            if users[uid]["admin"]:
                userweight_admin = CONFIG_admin_volunteer_weight
            else:
                userweight_admin = userweight_user

            bad, weight = evaluate_badness_of(value["result"])

            # Accumulate these to our buffers
            comment_weight_admin[cid] += userweight_admin * weight
            comment_weight_user[cid] += userweight_user * weight
            
            if bad:
                comment_badness_admin[cid] += userweight_admin * weight
                comment_badness_user[cid] += userweight_user * weight

        # Calculated badnesses, both taking admins into account and not doing so, and "theoretical idea" versus a conversative view designed to be more skeptical of low-weighted comments
        comment_calculated_badness_admin = {cid: calculate_final_comment_badness(comment_badness_admin[cid], comment_weight_admin[cid], False) for cid in reported_comment_ids}
        comment_calculated_badness_admin_conservative = {cid: calculate_final_comment_badness(comment_badness_admin[cid], comment_weight_admin[cid], True) for cid in reported_comment_ids}
        comment_calculated_badness_user = {cid: calculate_final_comment_badness(comment_badness_user[cid], comment_weight_user[cid], False) for cid in reported_comment_ids}
        comment_calculated_badness_user_conservative = {cid: calculate_final_comment_badness(comment_badness_user[cid], comment_weight_user[cid], True) for cid in reported_comment_ids}

        # go through user submissions and count up how good users seem to be at this
        user_correctness_weight = defaultdict(lambda: CONFIG_new_user_damping)
        user_correctness_value = defaultdict(lambda: CONFIG_default_user_accuracy * user_correctness_weight[0])

        for key, value in records_compiled.items():
            uid, cid = key

            # if this is "ignored", I don't trust that we have a real answer, so we just skip it for training purposes
            if commentresults[cid] == "ignored":
                continue

            bad, weight = evaluate_badness_of(value["result"])

            correctness, weight = evaluate_correctness_single(bad, weight, comment_calculated_badness_admin[cid])

            user_correctness_weight[uid] += weight
            user_correctness_value[uid] += correctness * weight

        # calculate new correctnesses
        for uid in reporting_user_ids:
            target_user_correctness = user_correctness_value[uid] / user_correctness_weight[uid]

            # lerp slowly to the new values
            user_accuracy[uid] = lerp(user_accuracy[uid], target_user_correctness, CONFIG_user_correctness_lerp)

    if diagnostics:
        # debug print

        from tabulate import tabulate
        
        commentscores = [{
            "link": f"https://themotte.org/comment/{cid}",
            "badness": comment_calculated_badness_admin[cid],
            "badnessuser": comment_calculated_badness_user[cid],
            "badnessusercons": comment_calculated_badness_user_conservative[cid],
            "participation": comment_weight_user[cid],
            "mh": commentresults[cid]} for cid in reported_comment_ids]
        commentscores.sort(key = lambda item: item["badnessusercons"] + item["badnessuser"] / 100)
        print(tabulate(commentscores, headers = "keys"))

        results = [{
                "user": f"https://themotte.org/@{users[uid]['username']}",
                "accuracy": user_accuracy[uid],
                "submit": users_compiled[uid]["submit"],
                "nonsubmit": sum(users_compiled[uid].values()) - users_compiled[uid]["submit"],
                "admin": users[uid]["admin"] and "Admin" or "",
            } for uid in reporting_user_ids]
        results.sort(key = lambda k: k["accuracy"])
        print(tabulate(results, headers = "keys"))

        dbg_commentdump(89681, records_compiled, users, user_accuracy)
        print(calculate_final_comment_badness(comment_badness_user[89681], comment_weight_user[89681], True))

        #dbg_userdump(131, records_compiled, users, comment_calculated_badness_user)

    # Shove all this in the database, yaaay
    # Conditional needed because sqlalchemy breaks if you try passing it zero data
    if len(user_accuracy) > 0:
        db.query(User) \
            .where(User.id.in_([id for id in user_accuracy.keys()])) \
            .update({
                User.volunteer_janitor_correctness: sqlalchemy.sql.case(
                    user_accuracy,
                    value = User.id,
                )
            })
        db.commit()

    # We don't bother recalculating comment confidences here; it's a pain to do it and they shouldn't change much

    logging.info("Finished full janitor recalculation")

@app.cli.command('volunteer_janitor_recalc')
def volunteer_janitor_recalc_cmd():
    volunteer_janitor_recalc(db_session(), diagnostics = True)

def volunteer_janitor_recalc_cron(ctx:TaskRunContext):
    volunteer_janitor_recalc(ctx.db)

def volunteer_janitor_recalc_all_comments(db: Session):
    # may as well do this first
    volunteer_janitor_recalc(db)

    # I'm not sure of the details here, but there seems to be some session-related caching cruft left around
    # so let's just nuke that
    db.expire_all()

    # going through all the comments piecemeal like this is hilariously efficient, but this entire system gets run exactly once ever, so, okay
    for comment in alive_it(db.query(Comment).join(Comment.reports)):
        update_comment_badness(db, comment.id)
    
    db.commit()

@app.cli.command('volunteer_janitor_recalc_all_comments')
def volunteer_janitor_recalc_all_comments_cmd():
    volunteer_janitor_recalc_all_comments(db_session())
