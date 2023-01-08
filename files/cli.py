from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

import files.classes

from .__main__ import app
from .commands.seed_db import seed_db

db = SQLAlchemy(app)
migrate = Migrate(app, db)
