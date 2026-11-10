'''
Changing a site setting (spec/admin/test_dashboard.py) replaces the settings file whole: every request re-reads it, so one arriving while the change is written must find either the old settings or the new, never a partly written file.
'''
import json

import pytest

from files.tests.spec.harness import as_user, assert_json_message, config, factories


@pytest.fixture
def reads_during_the_write(monkeypatch):
	'''Reads the settings file the way a concurrent request would, at the moment the new settings are serialised (recognised by holding every setting).'''
	seen = []
	with open(config.site_settings_path()) as f:
		keys = json.load(f).keys()

	def read(obj):
		if isinstance(obj, dict) and keys <= obj.keys():
			with open(config.site_settings_path()) as f:
				seen.append(f.read())

	real_dump, real_dumps = json.dump, json.dumps

	def dump(obj, fp, *args, **kwargs):
		read(obj)
		return real_dump(obj, fp, *args, **kwargs)

	def dumps(obj, *args, **kwargs):
		read(obj)
		return real_dumps(obj, *args, **kwargs)

	monkeypatch.setattr(json, "dump", dump)
	monkeypatch.setattr(json, "dumps", dumps)
	return seen


def test_a_request_during_a_setting_change_reads_whole_settings(reads_during_the_write):
	r = as_user(factories.admin(3)).post("/admin/site_settings/FilterNewPosts")

	assert_json_message(r)
	# The new settings were serialised, so the read above happened during the write
	assert reads_during_the_write
	for content in reads_during_the_write:
		assert isinstance(json.loads(content), dict), content
