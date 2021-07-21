from flask import render_template, request, g
from sqlalchemy import *
from sqlalchemy.orm import relationship, deferred
import re, random
from urllib.parse import urlparse
from .mix_ins import *
from ruqqus.helpers.base36 import *
from ruqqus.helpers.lazy import lazy
from ruqqus.__main__ import Base

class SubmissionAux(Base):

	__tablename__ = "submissions_aux"

	# we don't care about this ID
	key_id = Column(BigInteger, primary_key=True)
	id = Column(BigInteger, ForeignKey("submissions.id"))
	title = Column(String(500), default=None)
	title_html = Column(String(500), default=None)
	url = Column(String(500), default=None)
	body = Column(String(10000), default="")
	body_html = Column(String(20000), default="")
	ban_reason = Column(String(128), default="")
	embed_url = Column(String(256), default="")
	meta_title=Column(String(512), default="")
	meta_description=Column(String(1024), default="")


class Submission(Base, Stndrd, Age_times, Scores, Fuzzing):

	__tablename__ = "submissions"

	id = Column(BigInteger, primary_key=True)
	submission_aux = relationship(
		"SubmissionAux",
		lazy="joined",
		uselist=False,
		innerjoin=True,
		primaryjoin="Submission.id==SubmissionAux.id")
	author_id = Column(BigInteger, ForeignKey("users.id"))
	repost_id = Column(BigInteger, ForeignKey("submissions.id"), default=0)
	edited_utc = Column(BigInteger, default=0)
	created_utc = Column(BigInteger, default=0)
	thumburl = Column(String, default=None)
	is_banned = Column(Boolean, default=False)
	views = Column(Integer, default=0)
	deleted_utc = Column(Integer, default=0)
	purged_utc = Column(Integer, default=0)
	distinguish_level = Column(Integer, default=0)
	gm_distinguish = Column(Integer, ForeignKey("boards.id"), default=0)
	distinguished_board = relationship("Board", lazy="joined", primaryjoin="Board.id==Submission.gm_distinguish")
	created_str = Column(String(255), default=None)
	stickied = Column(Boolean, default=False)
	is_pinned = Column(Boolean, default=False)
	private = Column(Boolean, default=False)
	_comments = relationship(
		"Comment",
		lazy="dynamic",
		primaryjoin="Comment.parent_submission==Submission.id",
		backref="submissions")
	domain_ref = Column(Integer, ForeignKey("domains.id"))
	domain_obj = relationship("Domain")
	flags = relationship("Flag", backref="submission")
	is_approved = Column(Integer, ForeignKey("users.id"), default=0)
	approved_utc = Column(Integer, default=0)
	board_id = Column(Integer, ForeignKey("boards.id"), default=None)
	original_board_id = Column(Integer, ForeignKey("boards.id"), default=None)
	over_18 = Column(Boolean, default=False)
	original_board = relationship(
		"Board", primaryjoin="Board.id==Submission.original_board_id")
	creation_ip = Column(String(64), default="")
	mod_approved = Column(Integer, default=None)
	accepted_utc = Column(Integer, default=0)
	has_thumb = Column(Boolean, default=False)
	post_public = Column(Boolean, default=True)
	score_hot = Column(Float, default=0)
	score_top = Column(Float, default=1)
	score_activity = Column(Float, default=0)
	is_offensive = Column(Boolean, default=False)
	is_nsfl = Column(Boolean, default=False)
	board = relationship(
		"Board",
		lazy="joined",
		innerjoin=True,
		primaryjoin="Submission.board_id==Board.id")
	author = relationship(
		"User",
		lazy="joined",
		innerjoin=True,
		primaryjoin="Submission.author_id==User.id")
	is_pinned = Column(Boolean, default=False)
	score_best = Column(Float, default=0)
	reports = relationship("Report", backref="submission")
	is_bot = Column(Boolean, default=False)

	upvotes = Column(Integer, default=1)
	downvotes = Column(Integer, default=0)
	creation_region=Column(String(2), default=None)

	app_id=Column(Integer, ForeignKey("oauth_apps.id"), default=None)
	oauth_app=relationship("OauthApp")

	approved_by = relationship(
		"User",
		uselist=False,
		primaryjoin="Submission.is_approved==User.id")

	# not sure if we need this
	reposts = relationship("Submission", lazy="joined", remote_side=[id])

	# These are virtual properties handled as postgres functions server-side
	# There is no difference to SQLAlchemy, but they cannot be written to

	ups = deferred(Column(Integer, server_default=FetchedValue()))
	downs = deferred(Column(Integer, server_default=FetchedValue()))
	comment_count = Column(Integer, server_default=FetchedValue())
	score = deferred(Column(Float, server_default=FetchedValue()))

	awards = relationship("AwardRelationship", lazy="joined")

	rank_hot = deferred(Column(Float, server_default=FetchedValue()))
	rank_fiery = deferred(Column(Float, server_default=FetchedValue()))
	rank_activity = deferred(Column(Float, server_default=FetchedValue()))
	rank_best = deferred(Column(Float, server_default=FetchedValue()))

	def __init__(self, *args, **kwargs):

		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time.time())
			kwargs["created_str"] = time.strftime(
				"%I:%M %p on %d %b %Y", time.gmtime(
					kwargs["created_utc"]))

		kwargs["creation_ip"] = request.remote_addr

		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Submission(id={self.id})>"

	@property
	@lazy
	def board_base36id(self):
		return base36encode(self.board_id)

	@property
	@lazy
	def is_deleted(self):
		return bool(self.deleted_utc)
		
	@property
	@lazy
	def hotscore(self):
		return 10000000*(self.upvotes - self.downvotes + 1)/(((self.age+3600)/1000)**(1.35))

	@property
	@lazy
	def score_disputed(self):
		return (self.upvotes+1) * (self.downvotes+1)

	@property
	def is_repost(self):
		return bool(self.repost_id)

	@property
	def is_archived(self):
		return false

	@property
	@lazy
	def fullname(self):
		return f"t2_{self.base36id}"	
		
	@property
	@lazy
	def permalink(self):

		output = self.title.lower()

		output = re.sub('&\w{2,3};', '', output)

		output = [re.sub('\W', '', word) for word in output.split()]
		output = [x for x in output if x][0:6]

		output = '-'.join(output)

		if not output:
			output = '-'

		return f"/post/{self.id}/{output}"

	@property
	def is_archived(self):

		now = int(time.time())

		cutoff = now - (60 * 60 * 24 * 180)

		return self.created_utc < cutoff

	def rendered_page(self, sort=None, comment=None, comment_info=None, v=None):

		# check for banned
		if v and v.admin_level >= 3:
			template = "submission.html"
		elif self.is_banned:
			template = "submission_banned.html"
		else:
			template = "submission.html"

		# load and tree comments
		# calling this function with a comment object will do a comment
		# permalink thing
		if "replies" not in self.__dict__ and "_preloaded_comments" in self.__dict__:
			self.tree_comments(comment=comment)

		# return template
		is_allowed_to_comment = self.board.can_comment(
			v) and not self.is_archived

		return render_template(template,
							   v=v,
							   p=self,
							   sort=sort,
							   linked_comment=comment,
							   comment_info=comment_info,
							   is_allowed_to_comment=is_allowed_to_comment,
							   render_replies=True,
							   )

	@property
	@lazy
	def domain(self):

		if not self.url:
			return "text post"
		domain = urlparse(self.url).netloc
		if domain.startswith("www."):
			domain = domain.split("www.")[1]
		return domain.replace("old.reddit.com", "reddit.com")

	def tree_comments(self, comment=None, v=None):

		comments = self.__dict__.get('_preloaded_comments',[])
		if not comments:
			return

		pinned_comment=[]

		index = {}
		for c in comments:

			if c.is_pinned and c.parent_fullname==self.fullname:
				pinned_comment+=[c]
				continue

			if c.parent_fullname in index:
				index[c.parent_fullname].append(c)
			else:
				index[c.parent_fullname] = [c]

		for c in comments:
			c.__dict__["replies"] = index.get(c.fullname, [])

		if comment:
			self.__dict__["replies"] = [comment]
		else:
			self.__dict__["replies"] = pinned_comment + index.get(self.fullname, [])

	@property
	def active_flags(self):
		if self.is_approved:
			return 0
		else:
			return len(self.flags)

	@property
	#@lazy
	def thumb_url(self):
		
		if self.over_18: return f"/assets/images/nsfw.png"
		elif self.has_thumb:
			if self.thumburl: return self.thumburl
			else: return f"https://s3.eu-central-1.amazonaws.com/i.ruqqus.ga/posts/{self.base36id}/thumb.png"
		elif self.is_image:
			return self.url
		else:
			return None

	def visibility_reason(self, v):


		if not v or self.author_id == v.id:
			return "this is your content."
		elif self.is_pinned:
			return "a guildmaster has pinned it."
		elif self.board.has_mod(v):
			return f"you are a guildmaster of +{self.board.name}."
		elif self.board.has_contributor(v):
			return f"you are an approved contributor in +{self.board.name}."
		elif v.admin_level >= 4:
			return "you are a Drama admin."

	@property

	def json_raw(self):
		data = {'author_name': self.author.username if not self.author.is_deleted else None,
				'permalink': self.permalink,
				'is_banned': bool(self.is_banned),
				'is_deleted': self.is_deleted,
				'created_utc': self.created_utc,
				'id': self.base36id,
				'fullname': self.fullname,
				'title': self.title,
				'is_nsfw': self.over_18,
				'is_nsfl': self.is_nsfl,
				'is_bot': self.is_bot,
				'thumb_url': self.thumb_url,
				'domain': self.domain,
				'is_archived': self.is_archived,
				'url': self.url,
				'body': self.body,
				'body_html': self.body_html,
				'created_utc': self.created_utc,
				'edited_utc': self.edited_utc or 0,
				'guild_name': self.board.name,
				'guild_id': base36encode(self.board_id),
				'comment_count': self.comment_count,
				'score': self.score_fuzzed,
				'upvotes': self.upvotes_fuzzed,
				'downvotes': self.downvotes_fuzzed,
				'award_count': self.award_count,
				'is_offensive': self.is_offensive,
				'meta_title': self.meta_title,
				'meta_description': self.meta_description,
				'voted': self.voted
				}
		if self.ban_reason:
			data["ban_reason"]=self.ban_reason

		if self.board_id != self.original_board_id and self.original_board:
			data['original_guild_name'] = self.original_board.name
			data['original_guild_id'] = base36encode(self.original_board_id)
		return data

	@property
	def json_core(self):

		if self.is_banned:
			return {'is_banned': True,
					'is_deleted': self.is_deleted,
					'ban_reason': self.ban_reason,
					'id': self.base36id,
					'title': self.title,
					'permalink': self.permalink,
					'guild_name': self.board.name
					}
		elif self.is_deleted:
			return {'is_banned': bool(self.is_banned),
					'is_deleted': True,
					'id': self.base36id,
					'title': self.title,
					'permalink': self.permalink,
					'guild_name': self.board.name
					}

		return self.json_raw

	@property
	def json(self):

		data=self.json_core
		
		if self.deleted_utc > 0 or self.is_banned:
			return data

		data["author"]=self.author.json_core
		data["guild"]=self.board.json_core
		data["original_guild"]=self.original_board.json_core if not self.board_id==self.original_board_id else None
		data["comment_count"]=self.comment_count

	
		if "replies" in self.__dict__:
			data["replies"]=[x.json_core for x in self.replies]

		if "_voted" in self.__dict__:
			data["voted"] = self._voted

		return data

	@property
	def voted(self):
		return self._voted if "_voted" in self.__dict__ else 0

	@property
	def user_title(self):
		return self._title if "_title" in self.__dict__ else self.author.title

	@property
	def title(self):
		return self.submission_aux.title

	@title.setter
	def title(self, x):
		self.submission_aux.title = x
		g.db.add(self.submission_aux)

	@property
	def url(self):
		return self.submission_aux.url

	@url.setter
	def url(self, x):
		self.submission_aux.url = x
		g.db.add(self.submission_aux)

	def realurl(self, v):
		if v and v.agendaposter and random.randint(1, 10) < 4:
			return 'https://secure.actblue.com/donate/ms_blm_homepage_2019'
		elif self.url:
			if v and not v.oldreddit: return self.url.replace("old.reddit.com", "reddit.com")
			if self.url: return self.url
			return ""
 
	@property
	def body(self):
		return self.submission_aux.body

	@body.setter
	def body(self, x):
		self.submission_aux.body = x
		g.db.add(self.submission_aux)

	@property
	def body_html(self):
		return self.submission_aux.body_html

	@body_html.setter
	def body_html(self, x):
		self.submission_aux.body_html = x
		g.db.add(self.submission_aux)

	def realbody(self, v):
		body = self.submission_aux.body_html
		if not v or v.slurreplacer: body = body.replace(" nigger"," 🏀").replace(" Nigger"," 🏀").replace(" NIGGER"," 🏀").replace(" pedo"," libertarian").replace(" Pedo"," Libertarian ").replace(" PEDO"," LIBERTARIAN ").replace(" tranny"," 🚄").replace(" Tranny"," 🚄").replace(" TRANNY"," 🚄").replace("  fag","  cute twink").replace("  Fag","  Cute twink").replace("  FAG","  CUTE TWINK").replace(" faggot"," cute twink").replace(" Faggot"," Cute twink").replace(" FAGGOT"," CUTE TWINK").replace(" trump"," DDR").replace(" Trump"," DDR").replace(" TRUMP"," DDR").replace(" biden"," DDD").replace(" Biden"," DDD").replace(" BIDEN"," DDD").replace(" steve akins"," penny verity oaken").replace(" Steve Akins"," Penny Verity Oaken").replace(" STEVE AKINS"," PENNY VERITY OAKEN").replace(" RETARD"," RSLUR").replace(" rapist"," male feminist").replace(" Rapist"," Male feminist").replace(" RAPIST"," MALE FEMINIST").replace(" RETARD"," RSLUR").replace(" rapist"," male feminist").replace(" Rapist"," Male feminist").replace(" RAPIST"," MALE FEMINIST").replace(" RETARD"," RSLUR").replace(" rapist"," male feminist").replace(" Rapist"," Male feminist").replace(" RAPIST"," MALE FEMINIST").replace(" kill yourself"," keep yourself safe").replace(" KILL YOURSELF"," KEEP YOURSELF SAFE")
		if v and not v.oldreddit: body = body.replace("old.reddit.com", "reddit.com")
		return body

	@property
	def title_html(self):
		return self.submission_aux.title_html

	@title_html.setter
	def title_html(self, x):
		self.submission_aux.title_html = x
		g.db.add(self.submission_aux)

	def realtitle(self, v):
		if self.title_html: title = self.title_html
		else: title = self.title
		if not v or v.slurreplacer: title = title.replace(" nigger"," 🏀").replace(" Nigger"," 🏀").replace(" NIGGER"," 🏀").replace(" pedo"," libertarian").replace(" Pedo"," Libertarian ").replace(" PEDO"," LIBERTARIAN ").replace(" tranny"," 🚄").replace(" Tranny"," 🚄").replace(" TRANNY"," 🚄").replace("  fag","  cute twink").replace("  Fag","  Cute twink").replace("  FAG","  CUTE TWINK").replace(" faggot"," cute twink").replace(" Faggot"," Cute twink").replace(" FAGGOT"," CUTE TWINK").replace(" trump"," DDR").replace(" Trump"," DDR").replace(" TRUMP"," DDR").replace(" biden"," DDD").replace(" Biden"," DDD").replace(" BIDEN"," DDD").replace(" steve akins"," penny verity oaken").replace(" Steve Akins"," Penny Verity Oaken").replace(" STEVE AKINS"," PENNY VERITY OAKEN").replace(" RETARD"," RSLUR").replace(" rapist"," male feminist").replace(" Rapist"," Male feminist").replace(" RAPIST"," MALE FEMINIST").replace(" RETARD"," RSLUR").replace(" rapist"," male feminist").replace(" Rapist"," Male feminist").replace(" RAPIST"," MALE FEMINIST").replace(" RETARD"," RSLUR").replace(" rapist"," male feminist").replace(" Rapist"," Male feminist").replace(" RAPIST"," MALE FEMINIST").replace(" kill yourself"," keep yourself safe").replace(" KILL YOURSELF"," KEEP YOURSELF SAFE")
		return title

	@property
	def ban_reason(self):
		return self.submission_aux.ban_reason

	@ban_reason.setter
	def ban_reason(self, x):
		self.submission_aux.ban_reason = x
		g.db.add(self.submission_aux)

	@property
	def embed_url(self):
		return self.submission_aux.embed_url

	@embed_url.setter
	def embed_url(self, x):
		self.submission_aux.embed_url = x
		g.db.add(self.submission_aux)

	@property
	def meta_title(self):
		return self.submission_aux.meta_title

	@meta_title.setter
	def meta_title(self, x):
		self.submission_aux.meta_title=x
		g.db.add(self.submission_aux)

	@property
	def meta_description(self):
		return self.submission_aux.meta_description

	@meta_description.setter
	def meta_description(self, x):
		self.submission_aux.meta_description=x
		g.db.add(self.submission_aux)
	

	def is_guildmaster(self, perm=None):
		mod=self.__dict__.get('_is_guildmaster', False)

		if not mod:
			return False
		elif not perm:
			return True
		else:
			return mod.perm_full or mod.__dict__[f"perm_{perm}"]

		return output

	@property
	def is_blocking_guild(self):
		return self.__dict__.get('_is_blocking_guild', False)

	@property
	def is_blocked(self):
		return self.__dict__.get('_is_blocked', False)

	@property
	def is_blocking(self):
		return self.__dict__.get('_is_blocking', False)

	@property
	def is_subscribed(self):
		return self.__dict__.get('_is_subscribed', False)

	@property
	def is_public(self):
		return self.post_public or not self.board.is_private

	@property
	def flag_count(self):
		return len(self.flags)

	@property
	def report_count(self):
		return len(self.reports)

	@property
	def award_count(self):
		return len(self.awards)

	@property
	def embed_template(self):
		return f"site_embeds/{self.domain_obj.embed_template}.html"
	
	@property
	def flagged_by(self):
		return [x.user for x in self.flags]

	@property
	def is_image(self):
		if self.url: return self.url.endswith('jpg') or self.url.endswith('png') or self.url.endswith('.gif') or self.url.endswith('jpeg') or self.url.endswith('?maxwidth=9999') or self.url.endswith('?maxwidth=8888')
		else: return False

	@property
	def self_download_json(self):

		#This property should never be served to anyone but author and admin
		if not self.is_banned and self.deleted_utc == 0:
			return self.json_core

		data= {
			"title":self.title,
			"author": self.author.username,
			"url": self.url,
			"body": self.body,
			"body_html": self.body_html,
			"is_banned": bool(self.is_banned),
			"deleted_utc": self.deleted_utc,
			'created_utc': self.created_utc,
			'id': self.base36id,
			'fullname': self.fullname,
			'guild_name': self.board.name,
			'comment_count': self.comment_count,
			'permalink': self.permalink
		}

		if self.original_board_id and (self.original_board_id!= self.board_id):

			data['original_guild_name'] = self.original_board.name

		return data

	@property
	def json_admin(self):

		data=self.json_raw

		data["creation_ip"]=self.creation_ip
		data["creation_region"]=self.creation_region

		return data

	@property
	def is_exiled_for(self):
		return self.__dict__.get('_is_exiled_for', None)

	
	
class SaveRelationship(Base, Stndrd):

	__tablename__="save_relationship"

	id=Column(Integer, primary_key=true)
	user_id=Column(Integer, ForeignKey("users.id"))
	submission_id=Column(Integer, ForeignKey("submissions.id"))
	type=Column(Integer)
