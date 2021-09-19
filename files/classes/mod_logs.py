from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base
from .mix_ins import *
import time

class ModAction(Base, Stndrd, Age_times):
	__tablename__ = "modactions"
	id = Column(BigInteger, primary_key=True)

	user_id = Column(Integer, ForeignKey("users.id"))
	kind = Column(String(32))
	target_user_id = Column(Integer, ForeignKey("users.id"), default=0)
	target_submission_id = Column(Integer, ForeignKey("submissions.id"), default=0)
	target_comment_id = Column(Integer, ForeignKey("comments.id"), default=0)
	_note=Column(String(256), default=None)
	created_utc = Column(Integer, default=0)


	user = relationship("User", lazy="joined", primaryjoin="User.id==ModAction.user_id", viewonly=True)
	target_user = relationship("User", lazy="joined", primaryjoin="User.id==ModAction.target_user_id", viewonly=True)
	target_post = relationship("Submission", lazy="joined", viewonly=True)
	target_comment = relationship("Comment", lazy="joined", viewonly=True)


	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time.time())

		if "note" in kwargs:
			kwargs["_note"]=kwargs["note"]

		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<ModAction(id={self.id})>"


	@property
	def note(self):

		if self.kind=="ban_user":
			if self.target_post:
				return f'for <a href="{self.target_post.permalink}">post</a>'
			elif self.target_comment:
				return f'for <a href="{self.target_comment.permalink}">comment</a>'
			else: return self._note
		else:
			return self._note or ""

	@note.setter
	def note(self, x):
		self._note=x

	@property
	def string(self):

		output =  ACTIONTYPES[self.kind]["str"].format(self=self)

		if self.note: output += f" <i>({self.note})</i>"

		return output

	@property
	def target_link(self):
		if self.target_user:
			return f'<a href="{self.target_user.url}">{self.target_user.username}</a>'
		elif self.target_post:
			return f'<a href="{self.target_post.permalink}">{self.target_post.title}</a>'
		elif self.target_comment:
			return f'<a href="{self.target_comment.permalink}">comment</a>'

		else:
			return ""

	@property
	def icon(self):
		return ACTIONTYPES[self.kind]['icon']

	@property
	def color(self):
		return ACTIONTYPES[self.kind]['color']

	@property
	def permalink(self):
		return f"/log/{self.id}"	
	


ACTIONTYPES={
	"ban_user":{
		"str":'banned user {self.target_link}',
		"icon":"fa-user-slash",
		"color": "bg-danger",
	},
	"unban_user":{
		"str":'unbanned user {self.target_link}',
		"icon": "fa-user-slash",
		"color": "bg-muted",
	},
	"club_allow":{
		"str":'disallowed user {self.target_link} from the country club',
		"icon":"fa-user-slash",
		"color": "bg-danger",
	},
	"club_ban":{
		"str":'allowed user {self.target_link} into the country club',
		"icon": "fa-user-slash",
		"color": "bg-muted",
	},
	"nuke_user":{
		"str":'removed all content of {self.target_link}',
		"icon":"fa-user-slash",
		"color": "bg-danger",
	},
	"unnuke_user":{
		"str":'approved all content of {self.target_link}',
		"icon": "fa-user-slash",
		"color": "bg-muted",
	},
	"shadowban": {
		"str": 'shadowbanned {self.target_link}',
		"icon": "fa-user-slash",
		"color": "bg-danger",
	},
	"unshadowban": {
		"str": 'unshadowbanned {self.target_link}',
		"icon": "fa-user-slash",
		"color": "bg-muted",
	},
	"agendaposter": {
		"str": "set agendaposter theme on {self.target_link}",
		"icon": "fa-user-slash",
		"color": "bg-muted",
	},
	"unagendaposter": {
		"str": "removed agendaposter theme from {self.target_link}",
		"icon": "fa-user-slash",
		"color": "bg-muted",
	},
	"set_flair_locked":{
		"str":"set {self.target_link}'s flair (locked)",
		"icon": "fa-user-slash",
	},
	"set_flair_notlocked":{
		"str":"set {self.target_link}'s flair (not locked)",
		"icon": "fa-user-slash",
	},
	"pin_comment":{
		"str":'pinned a {self.target_link}',
		"icon":"fa-thumbtack fa-rotate--45",
		"color": "bg-info",
	},
	"unpin_comment":{
		"str":'un-pinned a {self.target_link}',
		"icon":"fa-thumbtack fa-rotate--45",
		"color": "bg-muted",
	},
	"pin_post":{
		"str":'pinned post {self.target_link}',
		"icon":"fa-thumbtack fa-rotate--45",
		"color": "bg-success",
	},
	"unpin_post":{
		"str":'un-pinned post {self.target_link}',
		"icon":"fa-thumbtack fa-rotate--45",
		"color": "bg-muted",
	},
	"set_nsfw":{
		"str":'set nsfw on post {self.target_link}',
		"icon":"fa-eye-evil",
		"color": "bg-danger",
	},
	"unset_nsfw":{
		"str":'un-set nsfw on post {self.target_link}',
		"icon":"fa-eye-evil",
		"color": "bg-muted",
	},
	"ban_post":{
		"str": 'removed post {self.target_link}',
		"icon":"fa-feather-alt",
		"color": "bg-danger",
	},
	"unban_post":{
		"str": 'reinstated post {self.target_link}',
		"icon":"fa-feather-alt",
		"color": "bg-muted",
	},
	"club":{
		"str": 'marked post {self.target_link} as viewable to users with +150 coins only',
		"icon":"fa-eye-slash",
		"color": "bg-danger",
	},
	"unclub":{
		"str": 'unmarked post {self.target_link} as viewable to users with +150 coins only',
		"icon":"fa-eye",
		"color": "bg-muted",
	},
	"ban_comment":{
		"str": 'removed {self.target_link}',
		"icon":"fa-comment",
		"color": "bg-danger",
	},
	"unban_comment":{
		"str": 'reinstated {self.target_link}',
		"icon":"fa-comment",
		"color": "bg-muted",
	},
}