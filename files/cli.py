from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from .__main__ import app
import files.classes

db = SQLAlchemy(app)
migrate = Migrate(app, db)
