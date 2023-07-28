
from files.classes.comment import Comment
from files.classes.volunteer_janitor import VolunteerJanitorRecord, VolunteerJanitorResult
from files.helpers.math import saturate, remap

# Returns (IsBad, Confidence)
def evaluate_badness_of(choice):
    if choice == VolunteerJanitorResult.Warning:
        return True, 1
    if choice == VolunteerJanitorResult.Ban:
        return True, 1
    
    # treating this like a low-weight bad response
    if choice == VolunteerJanitorResult.Bad:
        return True, 0.5
    
    # treating this like a low-weight not-bad response
    if choice == VolunteerJanitorResult.Neutral:
        return False, 0.5
    
    return False, 1

def userweight_from_user_accuracy(accuracy):
    return saturate(remap(accuracy, 0.5, 1, 0, 1))

def calculate_final_comment_badness(comment_total, comment_weight, conservative):
    if not conservative:
        # insert an artificial 50%-badness confident vote, to prevent us from ever reaching 1.0 or 0.0
        return (comment_total + 0.5) / (comment_weight + 1.0)
    
    if comment_weight == 0:
        # INSUFFICIENT DATA FOR A MEANINGFUL ANSWER
        return 0.5
    
    original_badness = calculate_final_comment_badness(comment_total, comment_weight, False)
    if original_badness > 0.5:
        # fake a not-bad vote, with the confidence being the opposite of our confidence in it being bad
        # don't let it invert though
        forged_weight = 1.0 - original_badness
        calculated_badness = max(comment_total / (comment_weight + forged_weight), 0.5)
    else:
        # fake a bad vote, with the confidence being the opposite of our confidence in it being not-bad
        # don't let it invert though
        forged_weight = original_badness
        calculated_badness = min((comment_total + forged_weight) / (comment_weight + forged_weight), 0.5)
    
    return calculated_badness

def update_comment_badness(db, cid, diagnostics: bool = False):
    # Recalculate the comment's confidence values
    # This probably does more SQL queries than it should
    records = db.query(VolunteerJanitorRecord) \
        .where(VolunteerJanitorRecord.comment_id == cid) \
        .order_by(VolunteerJanitorRecord.recorded_utc)

    user_has_pending = {}
    earliest_submission = {}

    for rec in records:
        if rec.result == VolunteerJanitorResult.Pending:
            user_has_pending[rec.user_id] = True
        else:
            if rec.user_id in user_has_pending:
                if rec.user_id not in earliest_submission or earliest_submission[rec.user_id].recorded_utc > rec.recorded_utc:
                    earliest_submission[rec.user_id] = rec
    
    badness = 0
    weight = 0

    for submission in earliest_submission.values():
        userweight_user = userweight_from_user_accuracy(submission.user.volunteer_janitor_correctness);
        submission_bad, submission_weight = evaluate_badness_of(submission.result)

        additive_weight = submission_weight * userweight_user

        weight += additive_weight
        if submission_bad:
            badness += additive_weight

    comment_badness = calculate_final_comment_badness(badness, weight, True)

    db.query(Comment) \
        .where(Comment.id == cid) \
        .update({Comment.volunteer_janitor_badness: comment_badness})

    if diagnostics:
        print(f"Updated comment {cid} to {comment_badness}")
