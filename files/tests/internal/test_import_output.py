'''Starting the site prints nothing on stdout, which a command's output shares: what a command prints there is its report alone. Start-up notes go to stderr.'''
import os
import subprocess

from files.tests.testenv import REPO_ROOT


def test_importing_the_site_prints_nothing_on_stdout():
	# The test environment's configuration, with the limiter off, as the tests run it
	result = subprocess.run(["python3", "-c", "import files.__main__"], cwd=REPO_ROOT, env=os.environ, capture_output=True, text=True)

	assert result.returncode == 0, result.stderr
	assert result.stdout == ""
