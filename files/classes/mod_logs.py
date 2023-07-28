import logging
from copy import deepcopy

from sqlalchemy import *
from sqlalchemy.orm import relationship

from files.classes.base import CreatedBase
from files.helpers.config.const import *
from files.helpers.lazy import lazy


class ModAction(CreatedBase):
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

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"

	@property
	def note(self):
		if self.kind == "ban_user":
			if self.target_post: return f'for <a href="{self.target_post.permalink}">post</a>'
			elif self.target_comment_id: return f'for <a href="/comment/{self.target_comment_id}">comment</a>'
			else: return self._note
		else:
			return self._note or ""

	@note.setter
	def note(self, x):
		self._note=x

	def lookup_action_type(self):
		if self.kind in ACTIONTYPES:
			return ACTIONTYPES[self.kind]
		else:
			logging.warning(f'Unfamiliar ACTIONTYPE {self.kind}')
			return ACTIONTYPES["fallback"]

	@property
	@lazy
	def string(self):
		output = self.lookup_action_type()["str"].format(self=self, cc=CC_TITLE)
		if not self.note: return output
		output += f" <i>({self.note})</i>"
		return output

	@property
	@lazy
	def target_link(self):
		if self.target_user: return f'<a href="{self.target_user.url}">{self.target_user.username}</a>'
		elif self.target_post:
			if self.target_post.club: return f'<a href="{self.target_post.permalink}">{CC} ONLY</a>'
			return f'<a href="{self.target_post.permalink}">{self.target_post.title_html}</a>'
		elif self.target_comment_id: return f'<a href="/comment/{self.target_comment_id}?context=8#context">comment</a>'

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
		"str": 'approved post {self.target_link}', 
		"icon": 'fa-feather-alt', 
		"color": 'bg-success'
	},
	'approve_comment': {
		"str": 'approved {self.target_link}', 
		"icon": 'fa-comment', 
		"color": 'bg-success'
	},
	'remove_post': {
		"str": 'removed post {self.target_link}', 
		"icon": 'fa-feather-alt', 
		"color": 'bg-danger'
	},
	'remove_comment': {
		"str": 'removed {self.target_link}', 
		"icon": 'fa-comment', 
		"color": 'bg-danger'
	},
	'approve_app': {
		"str": 'approved an application by {self.target_link}', 
		"icon": 'fa-robot', 
		"color": 'bg-success'
	},
	'badge_grant': {
		"str": 'granted badge to {self.target_link}', 
		"icon": 'fa-badge', 
		"color": 'bg-success'
	},
	'badge_remove': {
		"str": 'removed badge from {self.target_link}', 
		"icon": 'fa-badge', 
		"color": 'bg-danger'
	},
	'ban_domain': {
		"str": 'banned a domain', 
		"icon": 'fa-globe', 
		"color": 'bg-danger'
	},
	'ban_user': {
		"str": 'banned user {self.target_link}', 
		"icon": 'fa-user-slash', 
		"color": 'bg-danger'
	},
	'change_sidebar': {
		"str": 'changed the sidebar', 
		"icon": 'fa-columns', 
		"color": 'bg-primary'
	},
	'check': {
		"str": 'gave {self.target_link} a checkmark', 
		"icon": 'fa-badge-check', 
		"color": 'bg-success'
	},
	'club_allow': {
		"str": 'allowed user {self.target_link} into the {cc}', 
		"icon": 'fa-golf-club', 
		"color": 'bg-success'
	},
	'club_ban': {
		"str": 'disallowed user {self.target_link} from the {cc}', 
		"icon": 'fa-golf-club', 
		"color": 'bg-danger'
	},
	'delete_report': {
		"str": 'deleted report on {self.target_link}', 
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
		"str": 'distinguished {self.target_link}', 
		"icon": 'fa-crown', 
		"color": 'bg-success'
	},
	'distinguish_post': {
		"str": 'distinguished {self.target_link}', 
		"icon": 'fa-crown', 
		"color": 'bg-success'
	},
	'dump_cache': {
		"str": 'dumped cache', 
		"icon": 'fa-trash-alt', 
		"color": 'bg-muted'
	},
	'edit_post': {
		"str": 'edited {self.target_link}', 
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
		"str": 'set a flair on {self.target_link}', 
		"icon": 'fa-tag', 
		"color": 'bg-primary'
	},
	'grant_awards': {
		"str": 'granted awards to {self.target_link}', 
		"icon": 'fa-gift', 
		"color": 'bg-primary'
	},
	'link_accounts': {
		"str": 'linked {self.target_link}', 
		"icon": 'fa-link', 
		"color": 'bg-success'
	},
	'make_admin': {
		"str": 'made {self.target_link} admin', 
		"icon": 'fa-user-crown', 
		"color": 'bg-success'
	},
	'monthly': {
		"str": 'distributed monthly marseybux', 
		"icon": 'fa-sack-dollar', 
		"color": 'bg-success'
	},
	'nuke_user': {
		"str": 'removed all content of {self.target_link}', 
		"icon": 'fa-radiation-alt', 
		"color": 'bg-danger'
	},
	'pin_comment': {
		"str": 'pinned a {self.target_link}', 
		"icon": 'fa-thumbtack fa-rotate--45', 
		"color": 'bg-success'
	},
	'pin_post': {
		"str": 'pinned post {self.target_link}', 
		"icon": 'fa-thumbtack fa-rotate--45', 
		"color": 'bg-success'
	},
	'purge_cache': {
		"str": 'purged cache', 
		"icon": 'fa-memory', 
		"color": 'bg-muted'
	},
	'reject_app': {
		"str": 'rejected an application request by {self.target_link}', 
		"icon": 'fa-robot', 
		"color": 'bg-muted'
	},
	'remove_admin': {
		"str": 'removed {self.target_link} as admin', 
		"icon": 'fa-user-crown', 
		"color": 'bg-danger'
	},
	'revert': {
		"str": 'reverted {self.target_link} mod actions', 
		"icon": 'fa-history', 
		"color": 'bg-danger'
	},
	'revoke_app': {
		"str": 'revoked an application by {self.target_link}', 
		"icon": 'fa-robot', 
		"color": 'bg-muted'
	},
	'set_flair_locked': {
		"str": "set {self.target_link}'s flair (locked)", 
		"icon": 'fa-award', 
		"color": 'bg-primary'
	},
	'set_flair_notlocked': {
		"str": "set {self.target_link}'s flair (not locked)", 
		"icon": 'fa-award', 
		"color": 'bg-primary'
	},
	'set_nsfw': {
		"str": 'set nsfw on post {self.target_link}', 
		"icon": 'fa-eye-evil', 
		"color": 'bg-danger'
	},
	'shadowban': {
		"str": 'shadowbanned {self.target_link}', 
		"icon": 'fa-eye-slash', 
		"color": 'bg-danger'
	},
	'unban_domain': {
		"str": 'unbanned a domain', 
		"icon": 'fa-globe', 
		"color": 'bg-success'
	},
	'unban_user': {
		"str": 'unbanned user {self.target_link}', 
		"icon": 'fa-user', 
		"color": 'bg-success'
	},
	'uncheck': {
		"str": 'removed checkmark from {self.target_link}', 
		"icon": 'fa-badge-check', 
		"color": 'bg-muted'
	},
	'undistinguish_comment': {
		"str": 'un-distinguished {self.target_link}', 
		"icon": 'fa-crown', 
		"color": 'bg-muted'
	},
	'undistinguish_post': {
		"str": 'un-distinguished {self.target_link}', 
		"icon": 'fa-crown', 
		"color": 'bg-muted'
	},
	'unnuke_user': {
		"str": 'approved all content of {self.target_link}', 
		"icon": 'fa-radiation-alt', 
		"color": 'bg-success'
	},
	'unpin_comment': {
		"str": 'un-pinned a {self.target_link}', 
		"icon": 'fa-thumbtack fa-rotate--45', 
		"color": 'bg-muted'
	},
	'unpin_post': {
		"str": 'un-pinned post {self.target_link}', 
		"icon": 'fa-thumbtack fa-rotate--45', 
		"color": 'bg-muted'
	},
	'unset_nsfw': {
		"str": 'un-set nsfw on post {self.target_link}', 
		"icon": 'fa-eye-evil', 
		"color": 'bg-success'
	},
	'unshadowban': {
		"str": 'unshadowbanned {self.target_link}', 
		"icon": 'fa-eye', 
		"color": 'bg-success'
	},
	'fallback': {
		"str": 'unfamiliar action type, please report', 
		"icon": 'fa-robot', 
		"color": 'bg-muted'
	}
}

ACTIONTYPES2 = deepcopy(ACTIONTYPES)
ACTIONTYPES2.pop("shadowban")
ACTIONTYPES2.pop("unshadowban")
ACTIONTYPES2.pop("flair_post")
ACTIONTYPES2.pop("edit_post")
