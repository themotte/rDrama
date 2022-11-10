from collections import Counter
import unittest
from unittest import mock

import sqlparse

from easy_profile.reporters import shorten, StreamReporter


expected_table = """
|----------|--------|--------|--------|--------|--------|------------|
| Database | SELECT | INSERT | UPDATE | DELETE | Totals | Duplicates |
|----------|--------|--------|--------|--------|--------|------------|
| default  |   8    |   2    |   3    |   0    |   13   |     3      |
|----------|--------|--------|--------|--------|--------|------------|
"""

expected_table_stats = {
    "db": "default",
    "select": 8,
    "insert": 2,
    "update": 3,
    "delete": 0,
    "total": 13,
    "duration": 0.0345683,
    "duplicates": Counter({
        "SELECT id FROM users": 2,
        "SELECT id, name FROM users": 1,
    }),
    "duplicates_count": 3,
}


class TestShorten(unittest.TestCase):

    def test_shorten(self):
        # Test not longer string
        expected = "test"
        self.assertEqual(shorten(expected, len(expected)), expected)

        # Test longer string
        expected = "test..."
        self.assertEqual(shorten("test test", 7), expected)

        # Test with placeholder
        expected = "test!!!"
        self.assertEqual(shorten("test test", 7, placeholder="!!!"), expected)


class TestStreamReporter(unittest.TestCase):

    def test_initialization(self):
        mocked_file = mock.Mock()
        reporter = StreamReporter(
            medium=1,
            high=2,
            file=mocked_file,
            colorized=False,
            display_duplicates=0
        )
        self.assertEqual(reporter._medium, 1)
        self.assertEqual(reporter._high, 2)
        self.assertEqual(reporter._file, mocked_file)
        self.assertFalse(reporter._colorized)
        self.assertEqual(reporter._display_duplicates, 0)

    def test_initialization_default(self):
        reporter = StreamReporter()
        self.assertEqual(reporter._medium, 50)
        self.assertEqual(reporter._high, 100)
        self.assertTrue(reporter._colorized)
        self.assertEqual(reporter._display_duplicates, 5)

    def test_initialization_error(self):
        with self.assertRaises(ValueError):
            StreamReporter(medium=100, high=50)

    def test__colorize_on_deactivated(self):
        with mock.patch("easy_profile.reporters.colorize") as mocked:
            reporter = StreamReporter(colorized=False)
            reporter._colorize("test")
            mocked.assert_not_called()

    def test__colorize_on_activated(self):
        with mock.patch("easy_profile.reporters.colorize") as mocked:
            reporter = StreamReporter(colorized=True)
            reporter._colorize("test")
            mocked.assert_called()

    def test__info_line_on_high(self):
        with mock.patch.object(StreamReporter, "_colorize") as mocked:
            reporter = StreamReporter()
            reporter._info_line("test", reporter._high + 1)
            mocked.assert_called_with("test", ["bold"], fg="red")

    def test__info_line_on_medium(self):
        with mock.patch.object(StreamReporter, "_colorize") as mocked:
            reporter = StreamReporter()
            reporter._info_line("test", reporter._medium + 1)
            mocked.assert_called_with("test", ["bold"], fg="yellow")

    def test__info_line_on_low(self):
        with mock.patch.object(StreamReporter, "_colorize") as mocked:
            reporter = StreamReporter()
            reporter._info_line("test", reporter._medium - 1)
            mocked.assert_called_with("test", ["bold"], fg="green")

    def test_stats_table(self):
        reporter = StreamReporter(colorized=False)
        actual_table = reporter.stats_table(expected_table_stats)
        self.assertEqual(actual_table.strip(), expected_table.strip())

    def test_stats_table_change_sep(self):
        sep = "+"
        reporter = StreamReporter(colorized=False)
        actual_table = reporter.stats_table(expected_table_stats, sep=sep)
        expected = expected_table.replace("|", sep)
        self.assertEqual(actual_table.strip(), expected.strip())

    def test_report(self):
        dest = mock.Mock()
        reporter = StreamReporter(colorized=False, file=dest)
        reporter.report("test", expected_table_stats)

        expected_output = "\ntest"
        expected_output += expected_table

        total = expected_table_stats["total"]
        duration = expected_table_stats["duration"]
        summary = "\nTotal queries: {0} in {1:.3}s\n".format(total, duration)
        expected_output += summary

        actual_output = dest.write.call_args[0][0]
        self.assertRegexpMatches(actual_output, expected_output)

        for statement, count in expected_table_stats["duplicates"].items():
            statement = sqlparse.format(
                statement, reindent=True, keyword_case="upper"
            )
            text = "\nRepeated {0} times:\n{1}\n".format(count + 1, statement)
            self.assertRegexpMatches(actual_output, text)
