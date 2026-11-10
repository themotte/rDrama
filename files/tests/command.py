'''
One of the site's commands, run the way the out-of-process backend runs one (spec/harness/backend_process.py, RDRAMA_SPEC_CLI): `python3 -m files.tests.command <name> <arguments>`, as `flask <name> <arguments>` would, then doing the work the command handed to the background before exiting.
'''
from flask.cli import main

if __name__ == "__main__":
	try:
		main()
	finally:
		# Imported once the command has loaded the site and its configuration
		from files.helpers import background
		background.drain()
