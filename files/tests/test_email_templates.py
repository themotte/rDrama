"""Tests for email template rendering (#693).

Verifies that all email templates render without errors and use inline
styles instead of CSS classes (for email client compatibility).
"""
from . import util_accounts


def test_forgot_password_page_renders():
	"""Test that the forgot password page loads (entry point for password reset email)"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/forgot")
	assert response.status_code == 200
	assert "password" in response.text.lower()


def test_forgot_password_post_triggers_email_render():
	"""Test that posting to /forgot renders the password reset email template"""
	client, user = util_accounts.create_test_client_and_user(name="email-test")

	username = user.username
	client.get("/logout")

	# Post to forgot endpoint - even with wrong email, the template path is exercised
	response = client.post("/forgot", data={
		"username": username,
		"email": "test@example.com"
	})
	# Should return 200 with a message (not crash on template rendering)
	assert response.status_code == 200


def test_email_templates_no_css_classes():
	"""Verify email templates use inline styles, not CSS class references.

	Since the base email template (default.html) no longer has a <style> block,
	child templates must use inline styles for all visual formatting.
	"""
	from files.__main__ import app

	# List of email templates and their required context variables
	templates = {
		"email/password_reset.html": {"v": type("User", (), {"username": "test", "email": "test@example.com"})(), "action_url": "https://example.com/reset"},
		"email/email_change.html": {"v": type("User", (), {"username": "test", "email": "test@example.com"})(), "action_url": "https://example.com/verify"},
		"email/email_verify.html": {"v": type("User", (), {"username": "test", "email": "test@example.com"})(), "action_url": "https://example.com/verify"},
		"email/2fa_remove.html": {"action_url": "https://example.com/remove_2fa"},
	}

	css_classes_to_check = ["button-container", "button\"", "raw-link", "user-info", "reference-text"]

	with app.app_context():
		from flask import render_template
		for template_name, context in templates.items():
			html = render_template(template_name, **context)
			for css_class in css_classes_to_check:
				assert f'class="{css_class.rstrip(chr(34))}"' not in html, \
					f"Template {template_name} still uses CSS class '{css_class}' - should use inline styles"


def test_email_default_template_uses_table_layout():
	"""Verify the base email template uses table-based layout for email compatibility"""
	from files.__main__ import app

	with app.app_context():
		from flask import render_template
		html = render_template("email/password_reset.html",
			v=type("User", (), {"username": "test", "email": "test@example.com"})(),
			action_url="https://example.com/reset"
		)
		# Should use table-based layout (email best practice)
		assert "<table" in html
		assert 'role="presentation"' in html
		# Should NOT have a <style> block (inline styles only)
		assert "<style" not in html


def test_email_change_template_no_stray_closing_tag():
	"""Verify the stray </h1> after {% endblock %} in email_change.html is fixed"""
	import os
	template_path = os.path.join(
		os.path.dirname(os.path.dirname(__file__)),
		"templates", "email", "email_change.html"
	)
	with open(template_path) as f:
		content = f.read()
	# The old template had: {% endblock %}</h1> which is invalid
	assert "endblock %}</h1>" not in content
