from sqlalchemy import *
from sqlalchemy.orm import relationship
from ruqqus.__main__ import Base, cache
from .mix_ins import *
import time


class ModRelationship(Base, Age_times):
	__tablename__ = "mods"
	id = Column(BigInteger, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	board_id = Column(Integer, ForeignKey("boards.id"))
	created_utc = Column(Integer, default=0)
	accepted = Column(Boolean, default=False)
	invite_rescinded = Column(Boolean, default=False)

	perm_content = Column(Boolean, default=False)
	perm_appearance = Column(Boolean, default=False)
	perm_config = Column(Boolean, default=False)
	perm_access = Column(Boolean, default=False)
	perm_full = Column(Boolean, default=False)
	#permRules = Column(Boolean, default=False)
	#permTitles = Column(Boolean, default=False)
	#permLodges = Column(Boolean, default=False)

	user = relationship("User", lazy="joined")
	board = relationship("Board", lazy="joined")

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time.time())

		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Mod(id={self.id}, uid={self.user_id}, board_id={self.board_id})>"

	@property
	def permlist(self):
		if self.perm_full:
			return "full"

		output=[]
		for p in ["access","appearance", "config","content"]:
			if self.__dict__[f"perm_{p}"]:
				output.append(p)

		
		return ", ".join(output) if output else "none"

	@property
	def permchangelist(self):
		output=[]
		for p in ["full", "access","appearance", "config","content"]:
			if self.__dict__.get(f"perm_{p}"):
				output.append(f"+{p}")
			else:
				output.append(f"-{p}")

		return ", ".join(output)


	@property
	def json_core(self):
		return {
			'user_id':self.user_id,
			'board_id':self.board_id,
			'created_utc':self.created_utc,
			'accepted':self.accepted,
			'invite_rescinded':self.invite_rescinded,
			'perm_content':self.perm_full or self.perm_content,
			'perm_config':self.perm_full or self.perm_config,
			'perm_access':self.perm_full or self.perm_access,
			'perm_appearance':self.perm_full or self.perm_appearance,
			'perm_full':self.perm_full,
		}


	@property
	def json(self):
		data=self.json_core

		data["user"]=self.user.json_core
		#data["guild"]=self.board.json_core
	
		return data
	
	


class BanRelationship(Base, Stndrd, Age_times):

	__tablename__ = "bans"
	id = Column(BigInteger, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	board_id = Column(Integer, ForeignKey("boards.id"))
	created_utc = Column(BigInteger, default=0)
	banning_mod_id = Column(Integer, ForeignKey("users.id"))
	is_active = Column(Boolean, default=False)
	mod_note = Column(String(128), default="")

	user = relationship(
		"User",
		lazy="joined",
		primaryjoin="User.id==BanRelationship.user_id")
	banning_mod = relationship(
		"User",
		lazy="joined",
		primaryjoin="User.id==BanRelationship.banning_mod_id")
	board = relationship("Board")

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time.time())

		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Ban(id={self.id}, uid={self.uid}, board_id={self.board_id})>"

	@property
	def json_core(self):
		return {
			'user_id':self.user_id,
			'board_id':self.board_id,
			'created_utc':self.created_utc,
			'mod_id':self.banning_mod_id
		}


	@property
	def json(self):
		data=self.json_core

		data["user"]=self.user.json_core
		data["mod"]=self.banning_mod.json_core
		data["guild"]=self.board.json_core

		return data

class ContributorRelationship(Base, Stndrd, Age_times):

	__tablename__ = "contributors"
	id = Column(BigInteger, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	board_id = Column(Integer, ForeignKey("boards.id"))
	created_utc = Column(BigInteger, default=0)
	is_active = Column(Boolean, default=True)
	approving_mod_id = Column(Integer, ForeignKey("users.id"))

	user = relationship(
		"User",
		lazy="joined",
		primaryjoin="User.id==ContributorRelationship.user_id")
	approving_mod = relationship(
		"User",
		lazy='joined',
		primaryjoin="User.id==ContributorRelationship.approving_mod_id")
	board = relationship("Board", lazy="subquery")

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time.time())

		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Contributor(id={self.id}, uid={self.uid}, board_id={self.board_id})>"


class PostRelationship(Base):

	__tablename__ = "postrels"
	id = Column(BigInteger, primary_key=True)
	post_id = Column(Integer, ForeignKey("submissions.id"))
	board_id = Column(Integer, ForeignKey("boards.id"))

	post = relationship("Submission", lazy="subquery")
	board = relationship("Board", lazy="subquery")

	def __repr__(self):
		return f"<PostRel(id={self.id}, pid={self.post_id}, board_id={self.board_id})>"


class BoardBlock(Base, Stndrd, Age_times):

	__tablename__ = "boardblocks"

	id = Column(BigInteger, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	board_id = Column(Integer, ForeignKey("boards.id"))
	created_utc = Column(Integer)

	user = relationship("User")
	board = relationship("Board")

	def __repr__(self):
		return f"<BoardBlock(id={self.id}, uid={self.user_id}, board_id={self.board_id})>"
