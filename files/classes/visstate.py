from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

from files.helpers.config.const import PERMS

if TYPE_CHECKING:
	from files.classes.user import User
	from files.helpers.content import Submittable


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
	state, deleted information, and shadowban information. A decision to show
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
			op_name_safe=target.author_name
		)

	def moderated_body(self, v: User | None) -> str | None:
		if v and (v.admin_level >= PERMS['POST_COMMENT_MODERATION'] \
			or v.id == self.op_id):
			return None
		if self.deleted: return 'Deleted'
		if self.appear_removed(v): return 'Removed'
		if self.filtered: return 'Filtered'
		return None
	
	def visibility_and_message(self, v: User | None, is_blocking: bool) -> tuple[bool, str]:
		'''
		Returns a tuple of whether this content is visible and a publicly 
		visible message to accompany it. The visibility state machine is
		a slight mess but... this should at least unify the state checks.
		'''
		def can(v: User | None, perm_level: int) -> bool:
			return v and v.admin_level >= perm_level

		can_moderate: bool = can(v, PERMS['POST_COMMENT_MODERATION'])
		can_shadowban: bool = can(v, PERMS['USER_SHADOWBAN'])

		if v and v.id == self.op_id:
			return True, "This shouldn't be here, please report it!"
		if (self.removed and not can_moderate) or \
				(self.op_shadowbanned and not can_shadowban):
			msg: str = 'Removed'
			if self.state_mod_set_by:
				msg = f'Removed by @{self.state_mod_set_by}'
			return False, msg
		if self.filtered and not can_moderate:
			return False, 'Filtered'
		if self.deleted and not can_moderate:
			return False, 'Deleted by author'
		if is_blocking:
			return False, f'You are blocking @{self.op_name_safe}'
		return True, "This shouldn't be here, please report it!"
	
	def is_visible_to(self, v: User | None, is_blocking: bool) -> bool:
		return self.visibility_and_message(v, is_blocking)[0]
	
	def replacement_message(self, v: User | None, is_blocking: bool) -> str:
		return self.visibility_and_message(v, is_blocking)[1]
	
	def appear_removed(self, v: User | None) -> bool:
		if self.removed: return True
		if not self.op_shadowbanned: return False
		return (not v) or bool(v.admin_level < PERMS['USER_SHADOWBAN'])
	
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
