'''
The spec tier's whole vocabulary. Spec tests import from here and nowhere in `files` outside this package.
'''
import json

from files.tests.spec.harness import backend, config, db, factories
from files.tests.spec.harness.asserts import *
from files.tests.spec.harness.asserts import __all__ as _asserts_all
from files.tests.spec.harness.db import ANY, db_diff
from files.tests.spec.harness.http import Client, Response

__all__ = ["db", "factories", "ANY", "db_diff", "Client", "Response", "anon", "as_user", "site_settings_set", "run_background_work", *_asserts_all]


def anon() -> Client:
	return Client()


def as_user(user: dict) -> Client:
	return Client().login_as(user)


def site_settings_set(key, value):
	'''Changes one entry of the site settings file, which the app must re-read on every request (see config.site_settings_path).'''
	path = config.site_settings_path()
	with open(path) as f:
		settings = json.load(f)
	settings[key] = value
	with open(path, "w") as f:
		json.dump(settings, f)


def run_background_work():
	'''Runs work the app handed off to the background (thumbnail fetching, push notifications) to completion.'''
	backend.run_background_work()
