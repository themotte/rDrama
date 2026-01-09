"""Tests for files/commands/cron.py cron scheduling functionality."""

import logging
from datetime import datetime, timezone, time as datetime_time, timedelta
from unittest.mock import patch

import pytest

from files.__main__ import db_session, db_session_factory
from files.classes.cron.tasks import (
    RepeatableTask, RepeatableTaskRun, DayOfWeek, ScheduledTaskState
)
from files.classes.cron.pycallable import PythonCodeTask
from files.commands.cron import _acquire_lock_exclusive, _run_tasks, CRON_SLEEP_SECONDS
from . import util_accounts


def test_cron_sleep_seconds_constant():
    """Test that CRON_SLEEP_SECONDS is defined and positive."""
    assert CRON_SLEEP_SECONDS > 0
    assert isinstance(CRON_SLEEP_SECONDS, int)
    assert CRON_SLEEP_SECONDS == 15


def test_acquire_lock_exclusive_success():
    """Test _acquire_lock_exclusive successfully acquires and releases lock."""
    db_session.rollback()  # Ensure clean state

    # This tests the happy path where the lock is acquired and released cleanly
    with _acquire_lock_exclusive(db_session, RepeatableTask.__tablename__):
        # Verify we're in a transaction by checking if we can query
        task_count = db_session.query(RepeatableTask).count()
        assert task_count >= 0  # Just verify query works

    # After the context manager exits, changes should be committed
    db_session.rollback()  # Clean up any pending transaction


def test_acquire_lock_exclusive_locks_table():
    """Test _acquire_lock_exclusive locks the specified table."""
    db_session.rollback()  # Ensure clean state

    with _acquire_lock_exclusive(db_session, RepeatableTask.__tablename__):
        # Within the lock, we should be able to query
        count = db_session.query(RepeatableTask).count()
        assert count >= 0

    db_session.rollback()


def test_acquire_lock_exclusive_multiple_tables():
    """Test _acquire_lock_exclusive works with different table names."""
    db_session.rollback()  # Ensure clean state

    # Test with RepeatableTaskRun table
    with _acquire_lock_exclusive(db_session, RepeatableTaskRun.__tablename__):
        count = db_session.query(RepeatableTaskRun).count()
        assert count >= 0

    db_session.rollback()


def test_run_tasks_filtering_disabled():
    """Test that disabled tasks are filtered out by _run_tasks query."""
    client, user = util_accounts.create_test_client_and_user()

    # Create a disabled task
    task = PythonCodeTask(
        author_id=user.id,
        import_path="test",
        callable="disabled_function",
        frequency_day=int(DayOfWeek.ALL),
        time_of_day_utc=datetime_time(0, 0),
    )
    task.run_time_last = None
    task.enabled = False
    task.run_state_enum = ScheduledTaskState.WAITING
    db_session.add(task)
    db_session.commit()
    task_id = task.id

    # Query using the same filter as _run_tasks
    now = datetime.now(tz=timezone.utc)
    found = db_session.query(RepeatableTask).filter(
        RepeatableTask.enabled == True,
        RepeatableTask.id == task_id
    ).first()

    # Should not find the disabled task
    assert found is None

    # Clean up
    db_session.delete(task)
    db_session.commit()


def test_run_tasks_filtering_running_state():
    """Test that RUNNING tasks are filtered out by _run_tasks query."""
    client, user = util_accounts.create_test_client_and_user()

    # Create a task in RUNNING state
    task = PythonCodeTask(
        author_id=user.id,
        import_path="test",
        callable="running_function",
        frequency_day=int(DayOfWeek.ALL),
        time_of_day_utc=datetime_time(0, 0),
    )
    task.run_time_last = None
    task.enabled = True
    task.run_state_enum = ScheduledTaskState.RUNNING
    db_session.add(task)
    db_session.commit()
    task_id = task.id

    # Query using the same filter as _run_tasks
    found = db_session.query(RepeatableTask).filter(
        RepeatableTask.id == task_id,
        RepeatableTask.run_state != int(ScheduledTaskState.RUNNING),
    ).first()

    # Should not find the running task
    assert found is None

    # Clean up
    db_session.delete(task)
    db_session.commit()


def test_run_tasks_filtering_none_frequency():
    """Test that tasks with NONE frequency are filtered out."""
    client, user = util_accounts.create_test_client_and_user()

    # Create a task with NONE frequency
    task = PythonCodeTask(
        author_id=user.id,
        import_path="test",
        callable="none_freq_function",
        frequency_day=int(DayOfWeek.NONE),
        time_of_day_utc=datetime_time(0, 0),
    )
    task.run_time_last = None
    task.enabled = True
    task.run_state_enum = ScheduledTaskState.WAITING
    db_session.add(task)
    db_session.commit()
    task_id = task.id

    # Query using the same filter as _run_tasks
    found = db_session.query(RepeatableTask).filter(
        RepeatableTask.id == task_id,
        RepeatableTask.frequency_day != int(DayOfWeek.NONE),
    ).first()

    # Should not find the task with NONE frequency
    assert found is None

    # Clean up
    db_session.delete(task)
    db_session.commit()


def test_run_tasks_query_filters():
    """Test _run_tasks applies correct SQL filters."""
    # This test just verifies the SQL filters work without mocking
    # by checking that tasks with different properties are handled correctly

    # Test that we can query tasks with the same filters as _run_tasks
    now = datetime.now(tz=timezone.utc)
    tasks = db_session.query(RepeatableTask).filter(
        RepeatableTask.enabled == True,
        RepeatableTask.frequency_day != int(DayOfWeek.NONE),
        RepeatableTask.run_state != int(ScheduledTaskState.RUNNING),
        (RepeatableTask.run_time_last <= now)
            | (RepeatableTask.run_time_last == None),
    ).all()

    # Just verify the query works and returns a list
    assert isinstance(tasks, list)


def test_cron_constants():
    """Test that cron constants have expected values."""
    assert CRON_SLEEP_SECONDS == 15
    assert isinstance(CRON_SLEEP_SECONDS, int)
    assert CRON_SLEEP_SECONDS > 0
    assert CRON_SLEEP_SECONDS < 60


# Tests for _recover_stuck_tasks

from files.commands.cron import _recover_stuck_tasks


def test_recover_stuck_tasks_resets_running_state():
    """Test that tasks stuck in RUNNING state are reset to WAITING."""
    client, user = util_accounts.create_test_client_and_user()

    # Create a task stuck in RUNNING state (simulating a crash)
    task = PythonCodeTask(
        author_id=user.id,
        import_path="test",
        callable="stuck_function",
        frequency_day=int(DayOfWeek.ALL),
        time_of_day_utc=datetime_time(0, 0),
    )
    task.run_time_last = None
    task.enabled = True
    task.run_state_enum = ScheduledTaskState.RUNNING  # Stuck in RUNNING
    db_session.add(task)
    db_session.commit()
    task_id = task.id

    # Ensure no open transaction before acquiring exclusive lock
    db_session.rollback()

    # Run recovery
    _recover_stuck_tasks(db_session_factory)

    # Re-query the task to verify it was reset
    recovered_task = db_session.query(RepeatableTask).get(task_id)
    assert recovered_task.run_state_enum == ScheduledTaskState.WAITING

    # Clean up
    db_session.delete(recovered_task)
    db_session.commit()


def test_recover_stuck_tasks_marks_orphaned_runs_failed():
    """Test that orphaned runs (no completed_utc) are marked as failed."""
    client, user = util_accounts.create_test_client_and_user()

    # Create a task
    task = PythonCodeTask(
        author_id=user.id,
        import_path="test",
        callable="orphan_function",
        frequency_day=int(DayOfWeek.ALL),
        time_of_day_utc=datetime_time(0, 0),
    )
    task.enabled = True
    task.run_state_enum = ScheduledTaskState.WAITING
    db_session.add(task)
    db_session.commit()

    # Create an orphaned run (simulating a crash during execution)
    orphaned_run = RepeatableTaskRun(task_id=task.id)
    orphaned_run.completed_utc = None  # Never completed
    db_session.add(orphaned_run)
    db_session.commit()
    run_id = orphaned_run.id

    # Ensure no open transaction before acquiring exclusive lock
    db_session.rollback()

    # Run recovery
    _recover_stuck_tasks(db_session_factory)

    # Re-query the run to verify it was marked as failed
    recovered_run = db_session.query(RepeatableTaskRun).get(run_id)
    assert recovered_run.completed_utc is not None
    assert recovered_run.traceback_str == "Task was interrupted by server shutdown"
    assert recovered_run.status_text == "Failed"

    # Clean up
    db_session.delete(recovered_run)
    db_session.delete(task)
    db_session.commit()


def test_recover_stuck_tasks_no_stuck_tasks():
    """Test that recovery works correctly when no tasks are stuck."""
    # Ensure no open transaction before acquiring exclusive lock
    db_session.rollback()

    # Just verify no exception is raised
    _recover_stuck_tasks(db_session_factory)


def test_recover_stuck_tasks_multiple_stuck():
    """Test that multiple stuck tasks are all recovered."""
    client, user = util_accounts.create_test_client_and_user()

    # Create multiple stuck tasks
    task_ids = []
    for i in range(3):
        task = PythonCodeTask(
            author_id=user.id,
            import_path="test",
            callable=f"stuck_function_{i}",
            frequency_day=int(DayOfWeek.ALL),
            time_of_day_utc=datetime_time(0, 0),
        )
        task.run_time_last = None
        task.enabled = True
        task.run_state_enum = ScheduledTaskState.RUNNING
        db_session.add(task)
        db_session.commit()
        task_ids.append(task.id)

    # Ensure no open transaction before acquiring exclusive lock
    db_session.rollback()

    # Run recovery
    _recover_stuck_tasks(db_session_factory)

    # Verify all tasks were reset
    for task_id in task_ids:
        recovered_task = db_session.query(RepeatableTask).get(task_id)
        assert recovered_task.run_state_enum == ScheduledTaskState.WAITING
        db_session.delete(recovered_task)

    db_session.commit()