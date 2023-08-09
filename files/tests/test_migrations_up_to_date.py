import inspect
import migrations.versions
import os
import subprocess

from files.__main__ import app

APP_PATH = app.root_path
BASE_PATH = os.path.join(*os.path.split(APP_PATH)[:-1])
VERSIONS_PATH = migrations.versions.__path__._path[0]

def test_migrations_up_to_date():
	def get_versions():
		all_versions = [f.path for f in os.scandir(VERSIONS_PATH)]
		filtered_versions = []
		for entry in all_versions:
			if not os.path.isfile(entry):
				continue
			*dir_parts, filename = os.path.split(entry)
			base, ext = os.path.splitext(filename)
			if ext == '.py':
				filtered_versions.append(entry)
		return filtered_versions

	def get_method_body_lines(method):
		method_lines, _ = inspect.getsourcelines(method)
		return [l.strip() for l in method_lines if not l.strip().startswith('#')][1:]

	versions_before = get_versions()
	try:
		result = subprocess.run(
			[
				'python3',
				'-m',
				'flask',
				'db',
				'revision',
				'--autogenerate',
				'--rev-id=ci_verify_empty_revision',
				'--message=should_be_empty',
			],
			cwd=BASE_PATH,
			env={
				**os.environ,
				'FLASK_APP': 'files/cli:app',
			},
			capture_output=True,
			text=True,
			check=True
		)
	except subprocess.CalledProcessError as e:
		print("Failed to run migrations...")
		print(e.stderr)
		raise

	versions_after = get_versions()
	new_versions = [v for v in versions_after if v not in versions_before]
	try:
		for version in new_versions:
			filename = os.path.split(version)[-1]
			base, ext = os.path.splitext(filename)
			__import__(f'migrations.versions.{base}')
			migration = getattr(migrations.versions, base)
			upgrade_lines = get_method_body_lines(migration.upgrade)
			assert ["pass"] == upgrade_lines, "\n".join([
				"",
				"Expected upgrade script to be empty (pass) but got",
				*[f"\t>\t{l}" for l in upgrade_lines],
				"To fix this issue, please run",
				"\t$ flask db revision --autogenerate --message='short description of schema changes'",
				"to generate a candidate migration, and make any necessary changes to that candidate migration (e.g. naming foreign key constraints)",
			])
			downgrade_lines = get_method_body_lines(migration.downgrade)
			assert ["pass"] == downgrade_lines, "\n".join([
				"",
				"Expected downgrade script to be empty (pass) but got",
				*[f"\t>{l}" for l in downgrade_lines],
				"To fix this issue, please run",
				"\tflask db revision --autogenerate --message='short description of schema changes'",
				"to generate a candidate migration, and make any necessary changes to that candidate migration (e.g. naming foreign key constraints)",
			])
	finally:
		for version in new_versions:
			os.remove(version)
