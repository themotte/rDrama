'''
Advisory locks that serialize work on the same counters across transactions.
'''
from sqlalchemy import text
from sqlalchemy.orm import Session

# The first key of every advisory lock on a user's counted activity; the second is the user's id
_USER_COUNTS = 1


def user_counts_lock(db:Session, user_ids:list[int]):
	'''
	Waits for, then holds until the transaction ends, the right to cast the users' votes and create their posts and comments, the work that reads their shadowban to decide what counts. Locks in id order, so transactions locking several users can't deadlock each other.
	'''
	for user_id in sorted(set(user_ids)):
		db.execute(text("SELECT pg_advisory_xact_lock(:kind, :user)"), {"kind": _USER_COUNTS, "user": user_id})


def user_shadowbanned_locked(db:Session, user) -> bool:
	'''Locks the user's counts (see user_counts_lock) and reloads their shadowban as committed by now, so everything reading `user.shadowbanned` afterwards agrees; answers whether they are shadowbanned.'''
	user_counts_lock(db, [user.id])
	db.refresh(user, ["shadowbanned"])
	return bool(user.shadowbanned)
