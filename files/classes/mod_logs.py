import html
import logging

from sqlalchemy import *
from sqlalchemy.orm import relationship

from files.classes.base import CreatedDateTimeBase
from files.helpers.config.const import *
from files.helpers.lazy import lazy


class ModAction(CreatedDateTimeBase):
	__tablename__ = "modactions"
	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	kind = Column(String)
	target_user_id = Column(Integer, ForeignKey("users.id"))
	target_submission_id = Column(Integer, ForeignKey("submissions.id"))
	target_comment_id = Column(Integer, ForeignKey("comments.id"))
	_note=Column(String)

	Index('fki_modactions_user_fkey', target_user_id)
	Index('modaction_action_idx', kind)
	Index('modaction_cid_idx', target_comment_id)
	Index('modaction_id_idx', id.desc())
	Index('modaction_pid_idx', target_submission_id)

	user = relationship("User", primaryjoin="User.id==ModAction.user_id", viewonly=True)
	target_user = relationship("User", primaryjoin="User.id==ModAction.target_user_id", viewonly=True)
	target_post = relationship("Submission", viewonly=True)
	target_comment = relationship("Comment", viewonly=True)

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"

	def _hides_target_from(self, v) -> bool:
		'''Whether the post or comment this entry is about is one `v` couldn't open: a draft hidden from them, a comment on one or a private message they aren't party to, or something whose author's shadowban hides it from them.'''
		if self.target_post: return self.target_post.is_draft_hidden_from(v) or self.target_post.shadowban_hides_from(v)
		return not self.target_comment.is_open_to(v) or self.target_comment.shadowban_hides_from(v)

	def note_for(self, v) -> str:
		if self.kind == "ban_user" and (self.target_post or self.target_comment):
			what = "post" if self.target_post else "comment"
			if self._hides_target_from(v): return f"for {what}"
			href = self.target_post.permalink if self.target_post else f"/comment/{self.target_comment_id}"
			return f'for <a href="{href}">{what}</a>'
		# Notes hold text admins typed (reasons, flair, domains).
		return html.escape(self._note or "")

	def lookup_action_type(self):
		if self.kind in ACTIONTYPES:
			return ACTIONTYPES[self.kind]
		else:
			logging.warning(f'Unfamiliar ACTIONTYPE {self.kind}')
			return ACTIONTYPES["fallback"]

	def string_for(self, v) -> str:
		output = self.lookup_action_type()["str"].format(target_link=self.target_link_for(v))
		note = self.note_for(v)
		if not note: return output
		return output + f" <i>({note})</i>"

	def target_link_for(self, v) -> str | None:
		if self.target_user: return f'<a href="{self.target_user.url}">{self.target_user.username}</a>'
		elif self.target_post:
			if self._hides_target_from(v): return "a post"
			return f'post <a href="{self.target_post.permalink}">{self.target_post.title_html}</a>'
		elif self.target_comment:
			if self._hides_target_from(v): return "comment"
			return f'<a href="/comment/{self.target_comment_id}?context=8#context">comment</a>'

	@property
	@lazy
	def icon(self):
		return self.lookup_action_type()['icon']

	@property
	@lazy
	def color(self):
		return self.lookup_action_type()['color']

	@property
	@lazy
	def permalink(self):
		return f"/log/{self.id}"	

ACTIONTYPES = {
	'approve_post': {
		"str": 'approved {target_link}', 
		"icon": 'fa-feather-alt', 
		"color": 'bg-success'
	},
	'approve_comment': {
		"str": 'approved {target_link}', 
		"icon": 'fa-comment', 
		"color": 'bg-success'
	},
	'remove_post': {
		"str": 'removed {target_link}', 
		"icon": 'fa-feather-alt', 
		"color": 'bg-danger'
	},
	'remove_comment': {
		"str": 'removed {target_link}', 
		"icon": 'fa-comment', 
		"color": 'bg-danger'
	},
	'approve_app': {
		"str": 'approved an application by {target_link}', 
		"icon": 'fa-robot', 
		"color": 'bg-success'
	},
	'badge_grant': {
		"str": 'granted badge to {target_link}', 
		"icon": 'fa-badge', 
		"color": 'bg-success'
	},
	'badge_remove': {
		"str": 'removed badge from {target_link}', 
		"icon": 'fa-badge', 
		"color": 'bg-danger'
	},
	'ban_domain': {
		"str": 'banned a domain', 
		"icon": 'fa-globe', 
		"color": 'bg-danger'
	},
	'ban_user': {
		"str": 'banned user {target_link}', 
		"icon": 'fa-user-slash', 
		"color": 'bg-danger'
	},
	'change_sidebar': {
		"str": 'changed the sidebar', 
		"icon": 'fa-columns', 
		"color": 'bg-primary'
	},
	'check': {
		"str": 'gave {target_link} a checkmark', 
		"icon": 'fa-badge-check', 
		"color": 'bg-success'
	},
	'delete_report': {
		"str": 'deleted report on {target_link}', 
		"icon": 'fa-flag', 
		"color": 'bg-danger'
	},
	'disabled_Bots': {
		"str": 'disabled Bots', 
		"icon": 'fa-robot', 
		"color": 'bg-danger'
	},
	'disabled_FilterNewPosts': {
		"str": 'disabled filter new posts', 
		"icon": 'fa-filter', 
		"color": 'bg-danger'
	},
	'disabled_Read-only_mode': {
		"str": 'disabled readonly mode', 
		"icon": 'fa-book', 
		"color": 'bg-danger'
	},
	'disabled_Signups': {
		"str": 'disabled Signups', 
		"icon": 'fa-users', 
		"color": 'bg-danger'
	},
	'disabled_under_attack': {
		"str": 'disabled under attack mode', 
		"icon": 'fa-shield', 
		"color": 'bg-muted'
	},
	'distinguish_comment': {
		"str": 'distinguished {target_link}', 
		"icon": 'fa-crown', 
		"color": 'bg-success'
	},
	'distinguish_post': {
		"str": 'distinguished {target_link}', 
		"icon": 'fa-crown', 
		"color": 'bg-success'
	},
	'dump_cache': {
		"str": 'dumped cache', 
		"icon": 'fa-trash-alt', 
		"color": 'bg-muted'
	},
	'edit_post': {
		"str": 'edited {target_link}', 
		"icon": 'fa-edit', 
		"color": 'bg-primary'
	},
	'enabled_Bots': {
		"str": 'enabled Bots', 
		"icon": 'fa-robot', 
		"color": 'bg-success'
	},
	'enabled_FilterNewPosts': {
		"str": 'enabled filter new posts', 
		"icon": 'fa-filter', 
		"color": 'bg-success'
	},
	'enabled_Read-only_mode': {
		"str": 'enabled readonly mode', 
		"icon": 'fa-book', 
		"color": 'bg-success'
	},
	'enabled_Signups': {
		"str": 'enabled Signups', 
		"icon": 'fa-users', 
		"color": 'bg-success'
	},
	'enabled_under_attack': {
		"str": 'enabled under attack mode', 
		"icon": 'fa-shield', 
		"color": 'bg-success'
	},
	'flair_post': {
		"str": 'set a flair on {target_link}', 
		"icon": 'fa-tag', 
		"color": 'bg-primary'
	},
	'link_accounts': {
		"str": 'linked {target_link}', 
		"icon": 'fa-link', 
		"color": 'bg-success'
	},
	'make_admin': {
		"str": 'made {target_link} admin', 
		"icon": 'fa-user-crown', 
		"color": 'bg-success'
	},
	'nuke_user': {
		"str": 'removed all content of {target_link}', 
		"icon": 'fa-radiation-alt', 
		"color": 'bg-danger'
	},
	'pin_comment': {
		"str": 'pinned a {target_link}', 
		"icon": 'fa-thumbtack fa-rotate--45', 
		"color": 'bg-success'
	},
	'pin_post': {
		"str": 'pinned {target_link}', 
		"icon": 'fa-thumbtack fa-rotate--45', 
		"color": 'bg-success'
	},
	'purge_cache': {
		"str": 'purged cache', 
		"icon": 'fa-memory', 
		"color": 'bg-muted'
	},
	'reject_app': {
		"str": 'rejected an application request by {target_link}', 
		"icon": 'fa-robot', 
		"color": 'bg-muted'
	},
	'remove_admin': {
		"str": 'removed {target_link} as admin', 
		"icon": 'fa-user-crown', 
		"color": 'bg-danger'
	},
	'revert': {
		"str": 'reverted {target_link} mod actions', 
		"icon": 'fa-history', 
		"color": 'bg-danger'
	},
	'revoke_app': {
		"str": 'revoked an application by {target_link}', 
		"icon": 'fa-robot', 
		"color": 'bg-muted'
	},
	'set_flair_locked': {
		"str": "set {target_link}'s flair (locked)", 
		"icon": 'fa-award', 
		"color": 'bg-primary'
	},
	'set_flair_notlocked': {
		"str": "set {target_link}'s flair (not locked)", 
		"icon": 'fa-award', 
		"color": 'bg-primary'
	},
	'set_nsfw': {
		"str": 'set nsfw on {target_link}', 
		"icon": 'fa-eye-evil', 
		"color": 'bg-danger'
	},
	'shadowban': {
		"str": 'shadowbanned {target_link}', 
		"icon": 'fa-eye-slash', 
		"color": 'bg-danger'
	},
	'unban_domain': {
		"str": 'unbanned a domain', 
		"icon": 'fa-globe', 
		"color": 'bg-success'
	},
	'unban_user': {
		"str": 'unbanned user {target_link}', 
		"icon": 'fa-user', 
		"color": 'bg-success'
	},
	'uncheck': {
		"str": 'removed checkmark from {target_link}', 
		"icon": 'fa-badge-check', 
		"color": 'bg-muted'
	},
	'undistinguish_comment': {
		"str": 'un-distinguished {target_link}', 
		"icon": 'fa-crown', 
		"color": 'bg-muted'
	},
	'undistinguish_post': {
		"str": 'un-distinguished {target_link}', 
		"icon": 'fa-crown', 
		"color": 'bg-muted'
	},
	'unnuke_user': {
		"str": 'approved all content of {target_link}', 
		"icon": 'fa-radiation-alt', 
		"color": 'bg-success'
	},
	'unpin_comment': {
		"str": 'un-pinned a {target_link}', 
		"icon": 'fa-thumbtack fa-rotate--45', 
		"color": 'bg-muted'
	},
	'unpin_post': {
		"str": 'un-pinned {target_link}', 
		"icon": 'fa-thumbtack fa-rotate--45', 
		"color": 'bg-muted'
	},
	'unset_nsfw': {
		"str": 'un-set nsfw on {target_link}', 
		"icon": 'fa-eye-evil', 
		"color": 'bg-success'
	},
	'unshadowban': {
		"str": 'unshadowbanned {target_link}', 
		"icon": 'fa-eye', 
		"color": 'bg-success'
	},
	'filter_on': {
		"str": 'force-filtered {target_link}', 
		"icon": 'fa-user', 
		"color": 'bg-success'
	},
	'filter_off': {
		"str": 'unfiltered {target_link}', 
		"icon": 'fa-user', 
		"color": 'bg-success'
	},
	'filter_auto': {
		"str": 'autofiltered {target_link}', 
		"icon": 'fa-user', 
		"color": 'bg-success'
	},
	'fallback': {
		"str": 'unfamiliar action type, please report', 
		"icon": 'fa-robot', 
		"color": 'bg-muted'
	}
}

ADMIN_ONLY_KINDS = frozenset({"shadowban", "unshadowban", "flair_post", "edit_post", "link_accounts", "filter_on", "filter_off", "filter_auto"})
'''Kinds of mod action the mod log shows only to admins (level 2+).'''

ACTIONTYPES2 = {kind: t for kind, t in ACTIONTYPES.items() if kind not in ADMIN_ONLY_KINDS}
