
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

RECORD_ORDER = (VolunteerJanitorRecord.recorded_datetimez, VolunteerJanitorRecord.id)
'''The order records were stored in: by time, and by id among those stored at the same moment.'''


def counted_ratings(records) -> dict[tuple[int, int], VolunteerJanitorRecord]:
    '''The ratings that count among `records` (given in RECORD_ORDER), by (volunteer, comment): each volunteer's first rating of each comment after they were first assigned it.'''
    assigned = set()
    counted = {}
    for rec in records:
        key = (rec.user_id, rec.comment_id)
        if rec.result == VolunteerJanitorResult.Pending:
            assigned.add(key)
        elif key in assigned and key not in counted:
            counted[key] = rec
    return counted


def update_comment_badness(db, cid):
    # Recalculate the comment's confidence values
    # This probably does more SQL queries than it should

    # Recalculations of one comment take turns, so each counts the ratings the others stored
    db.query(Comment.id).where(Comment.id == cid).with_for_update().one()
    # The session doesn't autoflush: the records read below must include the ones just added
    db.flush()
    records = db.query(VolunteerJanitorRecord) \
        .where(VolunteerJanitorRecord.comment_id == cid) \
        .order_by(*RECORD_ORDER)

    badness = 0
    weight = 0

    for submission in counted_ratings(records).values():
        # Ratings by shadowbanned volunteers count for nothing, as their votes do
        if submission.user.shadowbanned:
            continue
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
