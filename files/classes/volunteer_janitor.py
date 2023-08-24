
from datetime import datetime
import enum

from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship

from files.classes.base import Base


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    comment_id: Mapped[int] = mapped_column(Integer, ForeignKey("comments.id"), nullable=False)
    recorded_utc: Mapped[datetime] = mapped_column(DateTime, default=0, nullable=False)
    result: Mapped[VolunteerJanitorResult] = mapped_column(Enum(VolunteerJanitorResult), default=VolunteerJanitorResult.Pending, nullable=False)

    Index('volunteer_comment_index', user_id, comment_id)

    user = relationship("User")
    comment = relationship("Comment")
