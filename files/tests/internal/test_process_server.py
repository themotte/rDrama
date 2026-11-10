'''The control requests the site answers when run for the out-of-process backend (files/tests/process_server.py), ahead of its own routes.'''
from werkzeug.test import Client

from files.helpers.background import spawn_background
from files.tests.process_server import BOOT, application
from files.tests.spec.harness import config
from files.tests.spec.harness.http import DEFAULT_USER_AGENT

client = Client(application)


def test_ready_answers_with_the_serving_process():
	r = client.post("/__spec__/ready")

	assert (r.status_code, r.json) == (200, {"boot": BOOT})


def test_held_background_work_runs_when_asked():
	ran = []
	spawn_background(ran.append, "work")

	r = client.post("/__spec__/background/run")

	assert (r.status_code, ran) == (200, ["work"])


def test_held_background_work_failing_is_answered_with_its_traceback():
	def fail():
		raise RuntimeError("probe failure")
	spawn_background(fail)

	r = client.post("/__spec__/background/run")

	assert r.status_code == 500 and "RuntimeError: probe failure" in r.get_data(as_text=True)


def test_discarded_background_work_never_runs():
	ran = []
	spawn_background(ran.append, "work")

	client.post("/__spec__/background/discard")
	client.post("/__spec__/background/run")

	assert ran == []


def test_other_requests_reach_the_site():
	site = {"Host": config.site_host(), "User-Agent": DEFAULT_USER_AGENT}
	assert client.get("/__spec__/ready", headers=site).status_code == 404
	assert client.post("/__spec__/elsewhere", headers=site).status_code == 404
