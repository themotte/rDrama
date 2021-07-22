from sqlalchemy import *
from flask import render_template
from drama.__main__ import Base

class Title(Base):

	__tablename__ = "titles"
	id = Column(Integer, primary_key=True)
	is_before = Column(Boolean, default=True)
	text = Column(String(64))
	qualification_expr = Column(String(256))
	requirement_string = Column(String(512))
	color = Column(String(6), default="888888")
	kind = Column(Integer, default=1)

	background_color_1 = Column(String(6), default=None)
	background_color_2 = Column(String(6), default=None)
	gradient_angle = Column(Integer, default=0)
	box_shadow_color = Column(String(32), default=None)
	text_shadow_color = Column(String(32), default=None)

	def check_eligibility(self, v):

		return bool(eval(self.qualification_expr, {}, {"v": v}))

	@property
	def rendered(self):
		return render_template('title.html', t=self)

	@property
	def json(self):

		return {'id': self.id,
				'text': self.text,
				'color': f'#{self.color}',
				'kind': self.kind
				}
