'''
The migration that sends every reply in a modmail thread to modmail, run on rows as older versions left them. The suite's database is migrated empty, so its data step is checked here.
'''
import importlib.util
import pathlib

from files.tests.spec.harness import db, db_diff, factories, seed

_PATH = next(pathlib.Path(__file__).parents[3].glob("migrations/versions/*_modmail_replies_sent_to_modmail.py"))


def _upgrade_sql():
	spec = importlib.util.spec_from_file_location("modmail_migration", _PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module.UPGRADE_SQL


def test_replies_in_modmail_threads_are_sent_to_modmail_and_nothing_else_changes():
	starter, admin, outsider = factories.user(), factories.admin(3), factories.user()
	modmail = factories.message(starter, seed.MODMAIL_ID)
	to_nobody = factories.message(admin, None, modmail)
	to_starter = factories.message(admin, starter, to_nobody)
	to_admin = factories.message(starter, admin, to_starter)
	intrusion = factories.message(outsider, starter, modmail)

	# Left alone: conversations between two users, replies to notices and private replies to comments on posts
	direct = factories.message(starter, admin)
	factories.message(admin, starter, direct)
	for author, sentto in ((seed.SYSTEM_ID, seed.SYSTEM_ID), (seed.AUTOJANNY_ID, seed.AUTOJANNY_ID)):
		factories.message(starter, sentto, factories.message(db.row("users", id=author), None))
	factories.message(starter, admin, factories.comment(admin, factories.post(admin)))

	with db_diff() as d:
		db.execute(_upgrade_sql())

	d.assert_exactly(updated={"comments": {c["id"]: {"sentto": seed.MODMAIL_ID} for c in (to_nobody, to_starter, to_admin, intrusion)}})
