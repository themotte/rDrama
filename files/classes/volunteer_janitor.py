
import enum
from files.classes.base import Base
from sqlalchemy import *
from sqlalchemy.orm import relationship
from sqlalchemy.sql.functions import now

class VolunteerJanitorResult(enum.Enum):
    Pending = 0
    TopQuality = 1
    Good = 2
    Neutral = 3
    Bad = 4
    Warning = 5
    Ban = 6

class VolunteerJanitorRecord(Base):
    __tablename__ = "volunteer_janitor"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False)
    recorded_datetimez = Column(DateTime(timezone=True), default=0, nullable=False, server_default=now())
    result = Column(Enum(VolunteerJanitorResult), default=VolunteerJanitorResult.Pending, nullable=False)

    Index('volunteer_comment_index', user_id, comment_id)

    user = relationship("User")
    comment = relationship("Comment")
