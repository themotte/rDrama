'''
A multipart upload whose file part declares no content type (browsers always send one; hand-made requests may not) is treated as not an image, not as an error. The spec harness's client always sends a type, so this builds the request by hand.
'''
from files.__main__ import app

BOUNDARY = "specboundary"


def _multipart(fields: dict, filename: str) -> bytes:
	parts = [f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items()]
	parts.append(f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n\r\nhello\r\n')
	return ("".join(parts) + f"--{BOUNDARY}--\r\n").encode()


def test_contact_form_upload_without_a_type_is_refused_as_not_an_image():
	r = app.test_client().post("/send_admin", data=_multipart({"message": "hi"}, "notes.txt"), content_type=f"multipart/form-data; boundary={BOUNDARY}")

	assert r.status_code == 400
