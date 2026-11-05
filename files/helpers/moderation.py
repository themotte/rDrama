from typing import Union

from files.classes import Comment, Submission, User
from files.classes.visstate import StateMod
from files.helpers.comments import comment_on_publish, comment_on_unpublish


def moderate(item:Union[Submission, Comment], state_mod:StateMod, by:str) -> int:
	'''
	Sets a post's or comment's moderation state on behalf of `by`, with the usual effects when that changes whether others can see it (counters, publish notifications, cached listings). Logs nothing.

	Returns 1 if the item became visible, -1 if it stopped being visible, else 0.
	'''
	was_visible = item.state_mod == StateMod.VISIBLE
	item.state_mod = state_mod
	item.state_mod_set_by = by
	is_visible = state_mod == StateMod.VISIBLE

	if is_visible and not was_visible:
		if isinstance(item, Comment): comment_on_publish(item)
		else: item.publish()
		return 1
	if was_visible and not is_visible:
		if isinstance(item, Comment): comment_on_unpublish(item)
		else: item.visibility_changed()
		return -1
	return 0


def shadowban_set(user:User, by:str) -> None:
	'''Shadowbans `user` on behalf of `by`. Logs nothing.'''
	user.shadowbanned = by


def shadowban_lift(user:User) -> None:
	'''Lifts `user`'s shadowban. Logs nothing.'''
	user.shadowbanned = None
