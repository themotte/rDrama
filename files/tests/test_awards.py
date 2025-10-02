"""Tests for awards routes (currently disabled)."""
from . import util_accounts


def test_shop_route_disabled():
	"""Test /shop route is disabled (returns 404)"""
	from files.__main__ import db_session
	client, user = util_accounts.create_test_client_and_user("shop-admin")
	user.admin_level = 2
	db_session.add(user)
	db_session.commit()

	response = client.get("/shop")
	assert response.status_code == 404


def test_settings_shop_route_disabled():
	"""Test /settings/shop route is disabled (returns 404)"""
	from files.__main__ import db_session
	client, user = util_accounts.create_test_client_and_user("shop-set-admin")
	user.admin_level = 2
	db_session.add(user)
	db_session.commit()

	response = client.get("/settings/shop")
	assert response.status_code == 404
