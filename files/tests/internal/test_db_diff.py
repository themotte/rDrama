import pytest

from files.tests.spec.harness.db import ANY, Diff


def test_inserted_rows_pair_up_regardless_of_expectation_order():
	diff = Diff(inserted={"votes": [{"user_id": 5, "vote_type": 1}, {"user_id": 6, "vote_type": 1}]})

	diff.assert_exactly(inserted={"votes": [{"vote_type": ANY}, {"user_id": 5}]})


def test_inserted_rows_must_all_be_expected():
	diff = Diff(inserted={"votes": [{"user_id": 5, "vote_type": 1}, {"user_id": 6, "vote_type": 1}]})

	with pytest.raises(AssertionError):
		diff.assert_exactly(inserted={"votes": [{"user_id": 5}]})


def test_unknown_columns_in_expectations_are_errors():
	diff = Diff(inserted={"votes": [{"user_id": 5, "vote_type": 1}]})

	with pytest.raises(AssertionError, match="no columns"):
		diff.assert_exactly(inserted={"votes": [{"usr_id": ANY}]})


def test_updates_must_list_exactly_the_changed_columns():
	diff = Diff(updated={"users": {(7,): {"bio": "a", "bio_html": "<p>a</p>"}}})

	diff.assert_exactly(updated={"users": {7: {"bio": "a", "bio_html": ANY}}})
	with pytest.raises(AssertionError):
		diff.assert_exactly(updated={"users": {7: {"bio": "a"}}})


def test_deletes_compare_keys_with_nulls():
	diff = Diff(deleted={"usernotes": [(1, None, 3), (1, 2, None)]})

	diff.assert_exactly(deleted={"usernotes": [(1, 2, None), (1, None, 3)]})
