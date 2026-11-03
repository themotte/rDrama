'''The post validator's embedding mode, which deployments switch with MULTIMEDIA_EMBEDDING_ENABLED (read once at startup, so out of the spec tier's reach).'''
from io import BytesIO

from flask import g, request

from files.__main__ import app, db_session
from files.helpers.validators import ValidatedSubmissionLike
from files.tests.spec.harness import uploads


def test_with_embedding_body_images_are_embedded_as_images():
	filename, content, content_type = uploads.png(20, 20)
	with app.test_request_context("/submit", method="POST", data={"title": "t", "body": "text", "file2": (BytesIO(content), filename, content_type)}):
		g.db = db_session()
		validated = ValidatedSubmissionLike.from_flask_request(request, allow_embedding=True)
	assert validated.body.startswith("text\n\n![](/images/") and validated.body.endswith(")")
