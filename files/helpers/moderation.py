from typing import Union

from files.classes import Comment, Submission, User
from files.classes.visstate import StateMod
from files.helpers.comments import comment_counts_shift_for_author, comment_state_change


def moderate(item:Union[Submission, Comment], state_mod:StateMod, by:str) -> int:
	'''
	Sets a post's or comment's moderation state on behalf of `by`, with the usual effects when that changes whether others can see it (counters, publish notifications, cached listings). Logs nothing.

	Returns 1 if the item became visible, -1 if it stopped being visible, else 0.
	'''
	was_visible = item.state_mod == StateMod.VISIBLE
	is_visible = state_mod == StateMod.VISIBLE

	if isinstance(item, Comment):
		with comment_state_change(item):
			item.state_mod = state_mod
			item.state_mod_set_by = by
	else:
		item.state_mod = state_mod
		item.state_mod_set_by = by
		if is_visible and not was_visible: item.publish()
		elif was_visible and not is_visible: item.visibility_changed()

	if is_visible and not was_visible: return 1
	if was_visible and not is_visible: return -1
	return 0


def shadowban_set(user:User, by:str) -> None:
	'''Shadowbans `user` on behalf of `by`, taking their comments out of the counts others see. Logs nothing.'''
	if not user.shadowbanned: comment_counts_shift_for_author(user.id, -1)
	user.shadowbanned = by


def shadowban_lift(user:User) -> None:
	'''Lifts `user`'s shadowban, counting their comments again (without notifying anyone of them). Logs nothing.'''
	if user.shadowbanned: comment_counts_shift_for_author(user.id, +1)
	user.shadowbanned = None
