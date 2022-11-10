import unittest

from easy_profile.termcolors import ansi_options, ansi_reset, colorize


class TestColorize(unittest.TestCase):

    def test_fg(self):
        colors = [
            "black", "red", "green", "yellow", "blue",
            "magenta", "cyan", "white"
        ]
        for color, code in dict(zip(colors, range(30, 38))).items():
            expected = "\033[{0}m".format(code) + "test" + ansi_reset
            self.assertEqual(colorize("test", fg=color), expected)

    def test_bg(self):
        colors = [
            "bright_black", "bright_red", "bright_green", "bright_yellow",
            "bright_blue", "bright_magenta", "bright_cyan", "bright_white"
        ]
        for color, code in dict(zip(colors, range(90, 98))).items():
            expected = "\033[{0}m".format(code + 10) + "test" + ansi_reset
            self.assertEqual(colorize("test", bg=color), expected)

    def test_options(self):
        for opt, code in ansi_options.items():
            expected = "\033[{0}m".format(code) + "test" + ansi_reset
            self.assertEqual(colorize("test", [opt]), expected)

    def test_noreset(self):
        self.assertEqual(colorize("test", ["noreset"]), "test")

    def test_reset(self):
        self.assertEqual(colorize("test", ["reset"]), ansi_reset)

    def test_complex(self):
        text = "test"
        expected = [
            "\033[30m",  # fg=black,
            "\033[1m",   # bold
            "\033[4m",   # underscore
            text,
            ansi_reset,
        ]
        actual = colorize(text, ["bold", "underscore"], fg="black")
        self.assertEqual(actual, "".join(expected))
