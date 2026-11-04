from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments

def test_send_message_to_user():
	"""Test sending a message to another user"""
	sender_client, sender_user = util_accounts.create_test_client_and_user("sender")
	receiver_client, receiver_user = util_accounts.create_test_client_and_user("receiver")

	# Senders need an approved post or comment before they can message
	util_submissions.create_submission_for_client(sender_client)

	message_text = util.generate_text()

	# Send message
	response, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": message_text}
	)

	assert response.status_code == 200
	assert "sent" in response.text.lower()

	# Verify message exists in database as a comment
	from files.__main__ import db_session
	from files.classes import Comment
	message = db_session.query(Comment).filter_by(
		author_id=sender_user.id,
		sentto=receiver_user.id
	).first()

	assert message is not None
	# Message body is stored in body_html after sanitization
	assert message.body_html is not None

def test_send_empty_message_rejected():
	"""Test that sending an empty message is rejected"""
	sender_client, sender_user = util_accounts.create_test_client_and_user("sender-empty")
	receiver_client, receiver_user = util_accounts.create_test_client_and_user("receiver-empty")

	util_submissions.create_submission_for_client(sender_client)

	# Try to send empty message
	response, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": ""}
	)

	assert response.status_code == 400
	assert "empty" in response.text.lower()

def test_send_duplicate_message_rejected():
	"""Test that sending duplicate messages is prevented"""
	sender_client, sender_user = util_accounts.create_test_client_and_user("sender-dup")
	receiver_client, receiver_user = util_accounts.create_test_client_and_user("receiver-dup")

	util_submissions.create_submission_for_client(sender_client)

	message_text = util.generate_text()

	# Send message first time
	response1, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": message_text}
	)
	assert response1.status_code == 200

	# Try to send exact same message again
	response2, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": message_text}
	)

	assert response2.status_code == 403
	assert "already exists" in response2.text.lower()

def test_send_message_requires_contribution():
	"""Users with no approved posts or comments can't send messages"""
	sender_client, sender_user = util_accounts.create_test_client_and_user("snd-nocontrib")
	receiver_client, receiver_user = util_accounts.create_test_client_and_user("rcv-nocontrib")

	response, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": util.generate_text()}
	)
	assert response.status_code == 403
	assert "part of the community" in response.text

	# Making a post lifts the restriction
	util_submissions.create_submission_for_client(sender_client)

	response, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": util.generate_text()}
	)
	assert response.status_code == 200
	assert "sent" in response.text.lower()

def test_send_message_to_admin_without_contribution():
	"""Messaging mods/admins is exempt from the contribution requirement"""
	sender_client, sender_user = util_accounts.create_test_client_and_user("snd-noc-adm")
	admin_client, admin_user = util_accounts.create_test_client_and_admin(2, "adm-msg-tgt")

	response, _ = util.post_with_formkey(
		sender_client, f"/@{admin_user.username}/message",
		data={"message": util.generate_text()}
	)
	assert response.status_code == 200
	assert "sent" in response.text.lower()

def test_reply_to_message_without_contribution():
	"""Replying to a received message is exempt from the contribution requirement"""
	sender_client, sender_user = util_accounts.create_test_client_and_user("snd-msg-rply")
	receiver_client, receiver_user = util_accounts.create_test_client_and_user("rcv-msg-rply")

	util_submissions.create_submission_for_client(sender_client)

	response, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": util.generate_text()}
	)
	assert response.status_code == 200

	from files.__main__ import db_session
	from files.classes import Comment
	message = db_session.query(Comment).filter_by(
		author_id=sender_user.id,
		sentto=receiver_user.id
	).first()
	assert message is not None

	# The receiver has no posts or comments but can still reply
	response, _ = util.post_with_formkey(
		receiver_client, "/reply",
		data={"parent_id": message.id, "body": util.generate_text()}
	)
	assert response.status_code == 200

	reply = db_session.query(Comment).filter_by(
		author_id=receiver_user.id,
		parent_comment_id=message.id
	).first()
	assert reply is not None

def test_user_message_route():
	"""Test POST /@<username>/message route"""
	client1, sender = util_accounts.create_test_client_and_user("sender")
	client2, recipient = util_accounts.create_test_client_and_user("recipient")

	util_submissions.create_submission_for_client(client1)

	response, _ = util.post_with_formkey(
		client1, f"/@{recipient.username}/message",
		data={"message": "Test message"}
	)
	assert response.status_code in [200, 302, 400]

def test_reply_route():
	"""Test POST /reply route"""
	client, user = util_accounts.create_test_client_and_user("replier")

	# Create a post and comment; /reply expects a comment ID (not a post ID)
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	response, _ = util.post_with_formkey(
		client, "/reply",
		data={"parent_id": comment.id, "body": "Test reply"}
	)
	assert response.status_code == 200
