from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from files.__main__ import app
from files.commands.cron import cron_app_worker
from files.commands.seed_db import seed_db
from files.commands.volunteer_janitor_recalc import volunteer_janitor_recalc
from files.commands.volunteer_janitor_histogram import volunteer_janitor_histogram_cmd
from files.commands.cron_setup import cron_setup
import files.classes

db = SQLAlchemy(app)
migrate = Migrate(app, db)
