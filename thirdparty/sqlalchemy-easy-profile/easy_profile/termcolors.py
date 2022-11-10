ansi_colors = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "bright_black": 90,
    "bright_red": 91,
    "bright_green": 92,
    "bright_yellow": 93,
    "bright_blue": 94,
    "bright_magenta": 95,
    "bright_cyan": 96,
    "bright_white": 97,
}

ansi_reset = "\033[0m"

ansi_options = {
    "bold": 1,
    "underscore": 4,
    "blink": 5,
    "reverse": 7,
    "conceal": 8,
}


def colorize(text, opts=(), fg=None, bg=None):
    """Colorize text enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold', 'underscore', 'blink', 'reverse', 'conceal'
        'noreset' - string will not be terminated with the reset code

    :param str text: your text
    :param tuple opts: text options
    :param str fg: foreground color name
    :param str bg: background color name

    :return: colorized text

    """
    codes = []
    if len(opts) == 1 and opts[0] == "reset":
        return ansi_reset

    if fg and fg in ansi_colors:
        codes.append("\033[{0}m".format(ansi_colors[fg]))
    elif bg and bg in ansi_colors:
        codes.append("\033[{0}m".format(ansi_colors[bg] + 10))

    for opt in opts:
        if opt in ansi_options:
            codes.append("\033[{0}m".format(ansi_options[opt]))

    if "noreset" not in opts:
        text += ansi_reset

    return "".join(codes) + text
