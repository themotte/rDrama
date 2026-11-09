from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import or_

from files.helpers.config.const import PERMS

if TYPE_CHECKING:
	from files.classes.user import User
	from files.helpers.content import Submittable


def sees_past_shadowbans(v) -> bool:
	'''Whether `v` is an admin who may see past shadowbans where the site lets them (level 2+).'''
	return bool(v) and v.admin_level >= PERMS['USER_SHADOWBAN']


def admin_sees_past_shadowban(v, *, is_message: bool, listed_on_authors_profile: bool) -> bool:
	'''Whether `v` sees, as an admin, an item its author's shadowban hides from others: private messages and modmail, and the shadowbanned user's posts and comments as their own profile lists them.'''
	return sees_past_shadowbans(v) and (is_message or listed_on_authors_profile)


class AuthorShadowban:
	'''For posts and comments: what their author's shadowban hides.'''

	is_message = False
	'''Comments without a post (private messages and modmail) say otherwise.'''

	@property
	def listed_on_authors_profile(self) -> bool:
		'''Whether this page lists it on its author's profile, which marks what it lists with its owner's id.'''
		return getattr(self, "listed_on_profile_of", None) == self.author_id

	def shadowban_hides_from(self, v) -> bool:
		'''Whether its author's shadowban hides it from `v`: from everyone but the author, and admins where they see past it.'''
		if not self.author.shadowbanned or (v and v.id == self.author_id): return False
		return not admin_sees_past_shadowban(v, is_message=self.is_message, listed_on_authors_profile=self.listed_on_authors_profile)

	@classmethod
	def shadowban_shown_sql(cls, v):
		'''The SQL condition that its author's shadowban doesn't hide an item from `v` in a listing (other than its author's profile): the author isn't shadowbanned, or is `v`.'''
		shown = cls.author.has(shadowbanned=None)
		return or_(shown, cls.author_id == v.id) if v else shown


class StateMod(enum.Enum):
    VISIBLE = 0
    FILTERED = 1
    REMOVED = 2

class StateReport(enum.Enum):
    UNREPORTED = 0
    RESOLVED = 1
    REPORTED = 2
    IGNORED = 3


@dataclass(frozen=True, kw_only=True, slots=True)
class VisibilityState:
	'''
	The full moderation state machine. It holds the moderation state, report
	state, deleted information, and shadowban information, with where the item
	is shown when that matters (on its author's profile). A decision to show
	or hide a post or comment should be able to be done with information from
	this alone.
	'''
	state_mod: StateMod
	state_mod_set_by: str | None
	state_report: StateReport
	state_mod_set_by: str | None
	deleted: bool
	op_shadowbanned: bool
	op_id: int
	op_name_safe: str
	distinguished: bool
	is_blocking: bool
	is_message: bool
	listed_on_authors_profile: bool

	@property
	def removed(self) -> bool:
		return self.state_mod == StateMod.REMOVED
	
	@property
	def filtered(self) -> bool:
		return self.state_mod == StateMod.FILTERED
	
	@property
	def reports_ignored(self) -> bool:
		return self.state_report == StateReport.IGNORED

	@classmethod
	def from_submittable(cls, target: Submittable) -> "VisibilityState":
		return cls(
			state_mod=target.state_mod,
			state_mod_set_by=target.state_mod_set_by, # type: ignore
			state_report=target.state_report,
			deleted=bool(target.state_user_deleted_utc != None),
			op_shadowbanned=bool(target.author.shadowbanned),
			op_id=target.author_id,  # type: ignore
			op_name_safe=target.author_name,
			distinguished=bool(getattr(target, 'distinguish_level', 0)),
			# Admins from level 2 may message users who block them
			is_blocking=bool(getattr(target, 'is_blocking', False)) and not (getattr(target, 'sentto', None) and target.author.account_admin_level >= PERMS['POST_COMMENT_MODERATION']),
			is_message=target.is_message,
			listed_on_authors_profile=target.listed_on_authors_profile,
		)
	
	def visibility_and_message(self, v: User | None) -> tuple[bool, str | None]:
		'''
		Returns a tuple of whether this content is visible and a publicly 
		visible message to accompany it. The visibility state machine is
		a slight mess but... this should at least unify the state checks.
		'''
		def can(v: User | None, perm_level: int) -> bool:
			return v and v.admin_level >= perm_level

		can_moderate: bool = can(v, PERMS['POST_COMMENT_MODERATION'])
		sees_past_shadowban: bool = admin_sees_past_shadowban(v, is_message=self.is_message, listed_on_authors_profile=self.listed_on_authors_profile)

		is_blocking = self.is_blocking
		
		if v and v.id == self.op_id:
			return True, None
		if (self.removed and not can_moderate) or \
				(self.op_shadowbanned and not sees_past_shadowban):
			msg: str = 'Removed'
			if self.removed and self.state_mod_set_by:
				msg = f'Removed by @{self.state_mod_set_by}'
			return False, msg
		if self.filtered and not can_moderate:
			return False, 'Filtered'
		if self.deleted and not can_moderate:
			return False, 'Deleted by author'
		if is_blocking and not can_moderate:
			if self.distinguished:
				return True, f'(You are blocking @{self.op_name_safe}, but this is an official post and cannot be blocked)'
			return False, f'You are blocking @{self.op_name_safe}'
		return True, None
	
	def is_visible_to(self, v: User | None) -> bool:
		return self.visibility_and_message(v)[0]
	
	def added_message(self, v: User | None) -> str | None:
		return self.visibility_and_message(v)[1]
	
	@property
	def publicly_visible(self) -> bool:
		return all(
			not state for state in 
			[self.deleted, self.removed, self.filtered, self.op_shadowbanned]
		)
	
	@property
	def explicitly_moderated(self) -> bool:
		'''
		Whether this was removed or filtered and not as the result of a shadowban
		'''
		return self.removed or self.filtered
