import re
from unittest.mock import patch

from assertpy import assert_that

from files.helpers import word_censor
from files.helpers.word_censor import create_variations_slur_regex, create_replace_map, censor_slurs, sub_matcher


def test_create_variations_slur_regex_for_slur_with_spaces():
    expected = [r"(\s|>)(retard)(\s|<)",
                r"(\s|>)(Retard)(\s|<)",
                r"(\s|>)(RETARD)(\s|<)"]

    result = create_variations_slur_regex(" retard ")

    assert_that(result).is_length(3).contains_only(*expected)


def test_create_variations_slur_regex_single_word():
    expected = [r"(\s|>)(retard)|(retard)(\s|<)",
                r"(\s|>)(Retard)|(Retard)(\s|<)",
                r"(\s|>)(RETARD)|(RETARD)(\s|<)"]

    result = create_variations_slur_regex("retard")

    assert_that(result).is_length(3).contains_only(*expected)


def test_create_variations_slur_regex_multiple_word():
    expected = [r"(\s|>)(kill yourself)|(kill yourself)(\s|<)",
                r"(\s|>)(Kill Yourself)|(Kill Yourself)(\s|<)",
                r"(\s|>)(Kill yourself)|(Kill yourself)(\s|<)",
                r"(\s|>)(KILL YOURSELF)|(KILL YOURSELF)(\s|<)"]
    result = create_variations_slur_regex("kill yourself")

    assert_that(result).is_length(4).contains_only(*expected)


@patch("files.helpers.word_censor.SLURS", {
    "tranny": "🚂🚃🚃",
    "kill yourself": "keep yourself safe",
    "faggot": "cute twink",
    " nig ": "🏀",
})
def test_create_replace_map():
    expected = {
        "tranny": "🚂🚃🚃",
        "Tranny": "🚂🚃🚃",
        "TRANNY": "🚂🚃🚃",
        "kill yourself": "keep yourself safe",
        "Kill yourself": "Keep yourself safe",
        "KILL YOURSELF": "KEEP YOURSELF SAFE",
        "Kill Yourself": "Keep Yourself Safe",
        "faggot": "cute twink",
        "Faggot": "Cute twink",
        "FAGGOT": "CUTE TWINK",
        "nig": "🏀",
        "Nig": "🏀",
        "NIG": "🏀",
    }
    result = create_replace_map()

    assert_that(result).is_equal_to(expected)


@patch("files.helpers.word_censor.REPLACE_MAP", {'retard': 'r-slur', 'NIG': '🏀'})
def test_sub_matcher():
    match = re.search(r"(\s|>)(retard)|(retard)(\s|<)", "<p>retard</p>")
    assert_that(sub_matcher(match)).is_equal_to(">r-slur")

    match = re.search(r"(\s|>)(retard)|(retard)(\s|<)", "<p>noretard</p>")
    assert_that(sub_matcher(match)).is_equal_to("r-slur<")

    match = re.search(r"(\s|>)(NIG)(\s|<)", "<p>NIG</p>")
    assert_that(sub_matcher(match)).is_equal_to(">🏀<")

    match = re.search(r"(\s|>)(NIG)(\s|<)", "<p>NIG </p>")
    assert_that(sub_matcher(match)).is_equal_to(">🏀 ")


@patch("files.helpers.word_censor.SLURS", {'retard': 'r-slur', 'manlet': 'little king', ' nig ': '🏀'})
def test_censor_slurs():
    word_censor.REPLACE_MAP = create_replace_map()

    assert_that(censor_slurs("<p>retard</p>", None)).is_equal_to("<p>r-slur</p>")
    assert_that(censor_slurs("<p>preretard</p>", None)).is_equal_to("<p>prer-slur</p>")
    assert_that(censor_slurs("that is Retarded like", None)).is_equal_to("that is R-slured like")
    assert_that(censor_slurs("that is SUPERRETARD like", None)).is_equal_to("that is SUPERR-SLUR like")
    assert_that(censor_slurs("<p>Manlets get out!</p>", None)).is_equal_to("<p>Little kings get out!</p>")

    assert_that(censor_slurs('... "retard" ...', None)).is_equal_to('... "retard" ...')
    assert_that(censor_slurs('... ReTaRd ...', None)).is_equal_to('... ReTaRd ...')
    assert_that(censor_slurs('... xretardx ...', None)).is_equal_to('... xretardx ...')

    assert_that(censor_slurs("LLM is a manlet hehe", None)).is_equal_to("LLM is a little king hehe")
    assert_that(censor_slurs("LLM is :marseycapitalistmanlet: hehe", None)) \
        .is_equal_to("LLM is :marseycapitalistmanlet: hehe")

    assert_that(censor_slurs('... Nig ...', None)).is_equal_to('... 🏀 ...')
    assert_that(censor_slurs('<p>NIG</p>', None)).is_equal_to('<p>🏀</p>')
    assert_that(censor_slurs('... nigeria ...', None)).is_equal_to('... nigeria ...')

    assert_that(censor_slurs("<p>retarded SuperManlet NIG</p>", None)) \
        .is_equal_to("<p>r-slured SuperLittle king 🏀</p>")


@patch("files.helpers.word_censor.SLURS", {'retard': 'r-slur', 'manlet': 'little king', ' nig ': '🏀'})
def test_censor_slurs_does_not_error_out_on_exception():
    word_censor.REPLACE_MAP = create_replace_map()
    word_censor.REPLACE_MAP["Manlet"] = None

    assert_that(censor_slurs(">retarded SuperManlet NIG<", None)).is_equal_to(">r-slured SuperManlet 🏀<")


@patch("files.helpers.word_censor.SLURS", {'retard': 'r-slur', 'manlet': 'little king'})
def test_censor_slurs_does_not_censor_on_flag_disabled():
    word_censor.REPLACE_MAP = create_replace_map()

    class User:
        def __init__(self, slurreplacer):
            self.slurreplacer = slurreplacer

    logger_user = User(slurreplacer=False)
    assert_that(censor_slurs("<p>retard</p>", logger_user)).is_equal_to("<p>retard</p>")

    logger_user = User(slurreplacer=True)
    assert_that(censor_slurs("<p>retard</p>", logger_user)).is_equal_to("<p>r-slur</p>")
