'''
GET /stats shows admins (level 2+) figures about the whole site, as of the request.
'''
from files.tests.spec.harness import *


def test_the_page_is_current_for_its_viewer():
	admin = factories.admin(2)
	client = as_user(admin)
	before = notification_counts(client.get("/stats"))["bell"]
	factories.notification(admin, factories.comment(factories.user(), factories.post(factories.user())))

	r = client.get("/stats")

	assert_html(r, 200)
	assert notification_counts(r)["bell"] == before + 1
