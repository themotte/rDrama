
from files.classes.base import CreatedDateTimeBase
from files.helpers.lazy import lazy
from sqlalchemy import *
from sqlalchemy.orm import declared_attr, relationship

class ChatMessage(CreatedDateTimeBase):
    __tablename__ = "chat_message"

    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quote_id = Column(Integer, ForeignKey("chat_message.id"), nullable=True)
    text = Column(String, nullable=False)
    text_html = Column(String, nullable=False)
    
    author = relationship("User", primaryjoin="User.id==ChatMessage.author_id")

    @declared_attr
    def created_datetimez_index(self):
        return Index('created_datetimez_index', self.created_datetimez)
    
    Index('quote_index', quote_id)
    
    @lazy
    def json_speak(self):
        data = {
               'id': str(self.id),
               'quotes': None if self.quote_id is None else str(self.quote_id),
               'avatar': self.author.profile_url,
               'username': self.author.username,
               'text': self.text,
               'text_html': self.text_html,
               'time': int(self.created_datetimez.timestamp()),
        }

        return data
