from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from files.__main__ import app
from files.commands.cron import cron_app_worker
from files.commands.seed_db import seed_db
from files.commands.cron_setup import cron_setup
import files.classes

db = SQLAlchemy(app)
migrate = Migrate(app, db)
