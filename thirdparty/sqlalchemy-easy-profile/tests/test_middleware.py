from queue import Queue
from threading import Thread
from time import sleep
import unittest
from unittest import mock

from easy_profile.middleware import EasyProfileMiddleware
from easy_profile.reporters import Reporter, StreamReporter


class TestEasyProfileMiddleware(unittest.TestCase):

    def test_initialization_default(self):
        mocked_app = mock.Mock()
        mw = EasyProfileMiddleware(mocked_app)
        self.assertEqual(mw.app, mocked_app)
        self.assertIs(mw.engine, None)
        self.assertIsInstance(mw.reporter, StreamReporter)
        self.assertEqual(mw.exclude_path, [])
        self.assertEqual(mw.min_time, 0)
        self.assertEqual(mw.min_query_count, 1)

    def test_initialize_custom(self):
        mocked_app = mock.Mock()
        mocked_reporter = mock.Mock(spec=Reporter)
        expected_exclude_path = ["/api/users"]
        mw = EasyProfileMiddleware(
            mocked_app,
            reporter=mocked_reporter,
            exclude_path=expected_exclude_path,
            min_time=42,
            min_query_count=42,
        )
        self.assertEqual(mw.app, mocked_app)
        self.assertEqual(mw.reporter, mocked_reporter)
        self.assertEqual(mw.exclude_path, expected_exclude_path)
        self.assertEqual(mw.min_time, 42)
        self.assertEqual(mw.min_query_count, 42)

    def test_initialize_reporter_type_error(self):
        with self.assertRaises(TypeError) as exec_info:
            EasyProfileMiddleware(mock.Mock(), reporter=mock.Mock())
        self.assertEqual(
            str(exec_info.exception),
            "reporter must be inherited from 'Reporter'"
        )

    def test__report_stats(self):
        mocked_reporter = mock.Mock(spec=Reporter)
        mw = EasyProfileMiddleware(
            mock.Mock(),
            reporter=mocked_reporter,
            min_time=42,
            min_query_count=42,
        )

        # Test that report called
        mw._report_stats("path", dict(total=43, duration=43))
        mw.reporter.report.assert_called()

        # Test that report not called
        mw.reporter = mock.Mock(spec=Reporter)
        mw._report_stats("path", dict(total=41, duration=41))
        mw.reporter.report.assert_not_called()

    def test__ignore_request(self):
        patterns = [r"^/api/users", r"^/api/roles", r"^/api/permissions"]
        mw = EasyProfileMiddleware(mock.Mock(), exclude_path=patterns)
        # Test unavailable path
        for path in ["/api/users", "/api/roles", "/api/permissions"]:
            self.assertTrue(mw._ignore_request(path))
        # Test available path
        for path in ["/faq", "/about", "/search"]:
            self.assertFalse(mw._ignore_request(path))

    def test__call__for_available_path(self):
        mw = EasyProfileMiddleware(
            mock.Mock(),
            reporter=mock.Mock(spec=Reporter),
            exclude_path=[r"^/api/users"]
        )
        with mock.patch.object(mw, "_report_stats") as mocked_report_stats:
            environ = dict(PATH_INFO="/api/roles", REQUEST_METHOD="GET")
            mw(environ, None)
            mocked_report_stats.assert_called()
            expected = environ["REQUEST_METHOD"] + " " + environ["PATH_INFO"]
            self.assertEqual(mocked_report_stats.call_args[0][0], expected)

    def test__call__for_unavailable_path(self):
        mw = EasyProfileMiddleware(
            mock.Mock(),
            reporter=mock.Mock(spec=Reporter),
            exclude_path=[r"^/api/users"]
        )
        with mock.patch.object(mw, "_report_stats") as mocked_report_stats:
            environ = dict(PATH_INFO="/api/users", REQUEST_METHOD="GET")
            mw(environ, None)
            mocked_report_stats.assert_not_called()

    def test__call__with_exception_triggered_when_getting_response(self):
        app = mock.Mock()
        app.side_effect = Exception("boom")
        mw = EasyProfileMiddleware(
            app=app,
            reporter=mock.Mock(spec=Reporter),
            exclude_path=[r"^/api/users"]
        )
        with mock.patch.object(mw, "_report_stats") as mocked_report_stats:
            environ = dict(PATH_INFO="/api/roles", REQUEST_METHOD="GET")
            with self.assertRaises(Exception):
                mw(environ, None)
            mocked_report_stats.assert_called()
            expected = environ["REQUEST_METHOD"] + " " + environ["PATH_INFO"]
            self.assertEqual(mocked_report_stats.call_args[0][0], expected)

    def test__call__with_multiple_concurrent_calls(self):
        fake_response = "fake response"

        def fake_call(*args, **kwargs):
            sleep(1)
            return fake_response

        mock_app = mock.Mock()
        mock_app.side_effect = fake_call
        mw = EasyProfileMiddleware(
            mock_app,
            reporter=mock.Mock(spec=Reporter),
            exclude_path=[r"^/api/users"]
        )

        thread_queue = Queue()
        threads = []
        repeats = 5

        with mock.patch.object(mw, "_report_stats"):
            environ = dict(PATH_INFO="/api/roles", REQUEST_METHOD="GET")
            for i in range(repeats):
                thread = Thread(
                    target=lambda queue, fn, env: queue.put(fn(env, None)),
                    args=(thread_queue, mw, environ)
                )
                thread.start()
                threads.append(thread)
        [thread.join() for thread in threads]

        results = []
        while not thread_queue.empty():
            results.append(thread_queue.get())

        assert len(results) == repeats
        assert set(results) == {fake_response}
