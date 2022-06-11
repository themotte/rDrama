from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from .__main__ import app
from .commands.seed_db import seed_db
import files.classes

db = SQLAlchemy(app)
migrate = Migrate(app, db)
