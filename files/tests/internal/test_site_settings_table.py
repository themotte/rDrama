'''
The site settings table (spec/harness/config.py SITE_SETTINGS) lists exactly the keys of the committed site_settings.json, with the kind of value each holds and its value there as the default, and each cites a spec file that names it.
'''
import json
import subprocess

from files.tests.spec.harness.config import SITE_SETTINGS
from files.tests.testenv import REPO_ROOT

SPEC = REPO_ROOT / "files" / "tests" / "spec"


def test_the_table_lists_the_committed_settings_their_kinds_and_defaults():
	# The committed file, not the working copy, which a local dev server's admin toggles rewrite
	committed = json.loads(subprocess.run(["git", "-c", "safe.directory=*", "show", "HEAD:site_settings.json"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout)

	assert {name: (type(value), value) for name, value in committed.items()} == {name: (setting.kind, setting.default) for name, setting in SITE_SETTINGS.items()}


def test_each_setting_cites_a_spec_file_naming_it():
	assert [name for name, setting in SITE_SETTINGS.items() if f'"{name}"' not in (SPEC / setting.spec).read_text()] == []
