'''
The migration that deletes tokens granted for API apps that aren't approved, as older versions let users grant them. The suite's database is migrated empty, so its data step is checked here.
'''
import importlib.util
import pathlib

from files.tests.spec.harness import db, db_diff, factories

_PATH = next(pathlib.Path(__file__).parents[3].glob("migrations/versions/*_drop_tokens_of_pending_oauth_apps.py"))


def _upgrade_sql():
	spec = importlib.util.spec_from_file_location("pending_tokens_migration", _PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module.UPGRADE_SQL


def test_tokens_of_pending_apps_are_deleted_and_nothing_else():
	owner, user = factories.user(), factories.user()
	pending, approved = factories.oauth_app(owner, state="pending"), factories.oauth_app(owner)
	for holder in (owner, user):
		factories.authorization(holder, pending)
	factories.authorization(user, approved)

	with db_diff() as d:
		db.execute(_upgrade_sql())

	d.assert_exactly(deleted={"client_auths": [(owner["id"], pending["id"]), (user["id"], pending["id"])]})
