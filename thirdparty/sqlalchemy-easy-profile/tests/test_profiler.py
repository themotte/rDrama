from collections import Counter
from queue import Queue
import time
import unittest
from unittest import mock

from sqlalchemy import create_engine, event
from sqlalchemy.engine.base import Engine

from easy_profile.profiler import DebugQuery, SessionProfiler, SQL_OPERATORS
from easy_profile.reporters import Reporter


debug_queries = [
    DebugQuery("SELECT id FROM users", {}, 1541489542, 1541489543),
    DebugQuery("SELECT id FROM users", {}, 1541489542, 1541489543),
    DebugQuery("SELECT name FROM users", {}, 1541489543, 1541489544),
    DebugQuery("SELECT gender FROM users", {}, 1541489544, 1541489545),
    DebugQuery(
        "INSERT INTO users (name) VALUES (%(param_1)s)",
        {"param_1": "Arthur Dent"},
        1541489545,
        1541489546
    ),
    DebugQuery(
        "INSERT INTO users (name) VALUES (%(param_1)s)",
        {"param_1": "Ford Prefect"},
        1541489546,
        1541489547
    ),
    DebugQuery(
        "UPDATE users SET name=(%(param_1)s)",
        {"param_1": "Prefect Ford"},
        1541489547,
        1541489548
    ),
    DebugQuery("DELETE FROM users", {}, 1541489548, 1541489549),
]


class TestSessionProfiler(unittest.TestCase):

    def test_initialization_default(self):
        profiler = SessionProfiler()
        self.assertIs(profiler.engine, Engine)
        self.assertEqual(profiler.db_name, "default")
        self.assertFalse(profiler.alive)
        self.assertIsNone(profiler.queries)

    def test_initialization_custom(self):
        engine = create_engine("sqlite:///test")
        profiler = SessionProfiler(engine)
        self.assertIs(profiler.engine, engine)
        self.assertEqual(profiler.db_name, "test")

    def test_begin(self):
        profiler = SessionProfiler()
        with mock.patch.object(profiler, "_reset_stats") as mocked:
            profiler.begin()
            mocked.assert_called()
            self.assertTrue(profiler.alive)
            self.assertIsInstance(profiler.queries, Queue)
            self.assertTrue(profiler.queries.empty())
            self.assertTrue(event.contains(
                profiler.engine,
                profiler._before,
                profiler._before_cursor_execute
            ))
            self.assertTrue(event.contains(
                profiler.engine,
                profiler._after,
                profiler._after_cursor_execute
            ))

    def test_begin_alive(self):
        profiler = SessionProfiler()
        profiler.alive = True
        with self.assertRaises(AssertionError) as exec_info:
            profiler.begin()

        error = exec_info.exception
        self.assertEqual(str(error), "Profiling session has already begun")

    def test_commit(self):
        profiler = SessionProfiler()
        profiler.begin()
        with mock.patch.object(profiler, "_get_stats") as mocked:
            profiler.commit()
            mocked.assert_called()
            self.assertFalse(profiler.alive)
            self.assertFalse(event.contains(
                profiler.engine,
                profiler._before,
                profiler._before_cursor_execute
            ))
            self.assertFalse(event.contains(
                profiler.engine,
                profiler._after,
                profiler._after_cursor_execute
            ))

    def test_commit_alive(self):
        profiler = SessionProfiler()
        profiler.alive = False
        with self.assertRaises(AssertionError) as exec_info:
            profiler.commit()

        error = exec_info.exception
        self.assertEqual(str(error), "Profiling session is already committed")

    def test__reset_stats(self):
        profiler = SessionProfiler()
        profiler._reset_stats()
        self.assertEqual(profiler._stats["total"], 0)
        self.assertEqual(profiler._stats["duration"], 0)
        self.assertEqual(profiler._stats["select"], 0)
        self.assertEqual(profiler._stats["insert"], 0)
        self.assertEqual(profiler._stats["update"], 0)
        self.assertEqual(profiler._stats["call_stack"], [])
        self.assertEqual(profiler._stats["duplicates"], Counter())
        self.assertEqual(profiler._stats["db"], profiler.db_name)

    def test__get_stats(self):
        profiler = SessionProfiler()
        profiler.queries = Queue()
        profiler._reset_stats()
        duplicates = Counter()
        for query in debug_queries:
            profiler.queries.put(query)
            duplicates_count = duplicates.get(query.statement, -1)
            duplicates[query.statement] = duplicates_count + 1

        stats = profiler._get_stats()

        for op in SQL_OPERATORS:
            res = filter(lambda x: op.upper() in x.statement, debug_queries)
            self.assertEqual(stats[op], len(list(res)))

        self.assertEqual(stats["db"], profiler.db_name)
        self.assertEqual(stats["total"], len(debug_queries))
        self.assertListEqual(debug_queries, stats["call_stack"])
        self.assertDictEqual(stats["duplicates"], duplicates)

    @mock.patch("easy_profile.profiler._timer")
    def test__before_cursor_execute(self, mocked):
        expected_time = time.time()
        mocked.return_value = expected_time
        profiler = SessionProfiler()
        context = mock.Mock()
        profiler._before_cursor_execute(
            conn=None,
            cursor=None,
            statement=None,
            parameters={},
            context=context,
            executemany=None
        )
        self.assertEqual(context._query_start_time, expected_time)

    @mock.patch("easy_profile.profiler._timer")
    def test__after_cursor_execute(self, mocked):
        expected_query = debug_queries[0]
        mocked.return_value = expected_query.end_time
        profiler = SessionProfiler()
        context = mock.Mock()
        context._query_start_time = expected_query.start_time
        with profiler:
            profiler._after_cursor_execute(
                conn=None,
                cursor=None,
                statement=expected_query.statement,
                parameters=expected_query.parameters,
                context=context,
                executemany=None
            )
            actual_query = profiler.queries.get()
            self.assertEqual(actual_query, expected_query)

    def test_stats(self):
        profiler = SessionProfiler()
        self.assertIsNotNone(profiler.stats)

    @mock.patch("easy_profile.profiler.SessionProfiler.begin")
    @mock.patch("easy_profile.profiler.SessionProfiler.commit")
    def test_contextmanager_interface(self, mocked_commit, mocked_begin):
        profiler = SessionProfiler()
        with profiler:
            mocked_begin.assert_called()
        mocked_commit.assert_called()

    def test_decorator(self):
        engine = self._create_engine()
        profiler = SessionProfiler(engine)
        wrapper = profiler()
        wrapper(self._decorated_func)(engine)
        # Test profile statistics
        self.assertEqual(profiler.stats["db"], "undefined")
        self.assertEqual(profiler.stats["total"], 4)
        self.assertEqual(profiler.stats["select"], 3)
        self.assertEqual(profiler.stats["delete"], 1)
        self.assertEqual(profiler.stats["duplicates_count"], 1)

    def test_decorator_path(self):
        expected_path = "test_path"
        engine = self._create_engine()
        profiler = SessionProfiler(engine)
        reporter = mock.Mock(spec=Reporter)
        # Get profiler decorator with specified path
        wrapper = profiler(path=expected_path, reporter=reporter)
        wrapper(self._decorated_func)(engine)
        # Test that reporter method report was called with expected path
        reporter.report.assert_called_with(expected_path, profiler.stats)

    def test_decorator_path_callback(self):
        expected_path = "path_callback"

        def _callback(func, *args, **kwargs):
            return expected_path

        engine = self._create_engine()
        profiler = SessionProfiler(engine)
        reporter = mock.Mock(spec=Reporter)
        # Get profiler decorator with specified path_callback
        wrapper = profiler(path_callback=_callback, reporter=reporter)
        wrapper(self._decorated_func)(engine)
        # Test that reporter method report was called with expected path
        reporter.report.assert_called_with(expected_path, profiler.stats)

    def test_decorator_path_and_path_callback(self):
        expected_path = "path_callback"

        def _callback(func, *args, **kwargs):
            return expected_path

        engine = self._create_engine()
        profiler = SessionProfiler(engine)
        reporter = mock.Mock(spec=Reporter)
        # Get profiler decorator with specified path_callback
        wrapper = profiler(
            path="fail",
            path_callback=_callback,
            reporter=reporter
        )
        wrapper(self._decorated_func)(engine)
        # Test that reporter method report was called with expected path
        reporter.report.assert_called_with(expected_path, profiler.stats)

    def _create_engine(self):
        """Creates and returns sqlalchemy engine."""
        return create_engine("sqlite://")

    def _decorated_func(self, engine):
        """Function for testing profiler as decorator."""
        engine.execute("CREATE TABLE users (id int, name varchar(8))")
        engine.execute("SELECT id FROM users")
        engine.execute("SELECT id FROM users")
        engine.execute("SELECT name FROM users")
        engine.execute("DELETE FROM users")
