'''What of the spec tier is handed over to another implementation: `git archive HEAD` of HANDED_OVER, which leaves out what .gitattributes marks export-ignore.'''
import subprocess
from pathlib import Path

from files.tests.testenv import REPO_ROOT

HANDED_OVER = ("files/__init__.py", "files/tests/__init__.py", "files/tests/spec")
'''The spec tier, and the package files above it, so that it imports as the package it is.'''


def _git(*args: str) -> str:
	return subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout


def exported() -> list[Path]:
	'''The files of the handover, with those not yet committed (and without those deleted but not yet committed).'''
	files = [f for f in _git("ls-files", "--cached", "--others", "--exclude-standard", "--", *HANDED_OVER).split() if (REPO_ROOT / f).exists()]
	attributes = _git("check-attr", "export-ignore", "--", *files).splitlines()
	ignored = {line.split(": ")[0] for line in attributes if line.endswith(": set")}
	return [REPO_ROOT / f for f in files if f not in ignored]


def repository_files() -> list[Path]:
	return [REPO_ROOT / f for f in _git("ls-files", "--cached", "--others", "--exclude-standard").split()]
