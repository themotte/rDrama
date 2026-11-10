'''
The site settings table (spec/harness/config.py SITE_SETTINGS) lists exactly the keys of the committed site_settings.json, with the kind of value each holds, and each cites a spec file that names it.
'''
import json

from files.tests.spec.harness.config import SITE_SETTINGS
from files.tests.testenv import REPO_ROOT

SPEC = REPO_ROOT / "files" / "tests" / "spec"


def test_the_table_lists_the_committed_settings_and_their_kinds():
	committed = json.loads((REPO_ROOT / "site_settings.json").read_text())

	assert {name: type(value) for name, value in committed.items()} == {name: setting.kind for name, setting in SITE_SETTINGS.items()}


def test_each_setting_cites_a_spec_file_naming_it():
	assert [name for name, setting in SITE_SETTINGS.items() if f'"{name}"' not in (SPEC / setting.spec).read_text()] == []
