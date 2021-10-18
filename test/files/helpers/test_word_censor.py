import re
from unittest.mock import patch

from assertpy import assert_that

from files.helpers import word_censor
from files.helpers.word_censor import create_replace_map, censor_slurs, sub_matcher, \
    get_permutations_slur, first_upper, first_all_upper, create_slur_regex


def test_first_upper():
    assert_that(first_upper("USS liberty")).is_equal_to("USS liberty")
    assert_that(first_upper("uss liberty")).is_equal_to("Uss liberty")
    assert_that(first_upper("uss Liberty")).is_equal_to("Uss Liberty")


def test_first_all_upper():
    assert_that(first_all_upper("USS liberty")).is_equal_to("USS Liberty")
    assert_that(first_all_upper("uss liberty")).is_equal_to("Uss Liberty")
    assert_that(first_all_upper("uss Liberty")).is_equal_to("Uss Liberty")


def test_get_permutations_slur():
    expected = {
        "USS liberty incident": "Tragic accident aboard the USS Liberty",
        "uss liberty incident": "tragic accident aboard the USS Liberty",
        "USS Liberty Incident": "Tragic Accident Aboard The USS Liberty",
        "USS LIBERTY INCIDENT": "TRAGIC ACCIDENT ABOARD THE USS LIBERTY",
    }

    result = get_permutations_slur("USS liberty incident", "tragic accident aboard the USS Liberty")

    assert_that(result).is_equal_to(expected)


def test_get_permutations_slur_wiht_link_replacer():
    expected = {
        "kike": "https://sciencedirect.com/science/article/abs/pii/S016028960600033X",
        "Kike": "https://sciencedirect.com/science/article/abs/pii/S016028960600033X",
        "KIKE": "https://sciencedirect.com/science/article/abs/pii/S016028960600033X",
    }

    result = get_permutations_slur("kike", "https://sciencedirect.com/science/article/abs/pii/S016028960600033X")

    assert_that(result).is_equal_to(expected)


@patch("files.helpers.word_censor.SLURS", {
    "kill yourself": "keep yourself safe",
    "faggot": "cute twink",
    " nig ": "🏀",
    " retard ": "r-slur",
})
def test_create_slur_regex():
    expected = r"(?i)(\s|>)(kill yourself|faggot)|(kill yourself|faggot)(\s|<)|(\s|>)(nig|retard)(\s|<)"

    assert_that(create_slur_regex()).is_equal_to(re.compile(expected))


@patch("files.helpers.word_censor.SLURS", {
    "tranny": "🚂🚃🚃",
    "kill yourself": "keep yourself safe",
    "faggot": "cute twink",
    "NoNewNormal": "NoNewNormal",
    " nig ": "🏀",
})
def test_create_replace_map():
    expected = {
        "tranny": "🚂🚃🚃",
        "Tranny": "🚂🚃🚃",
        "TRANNY": "🚂🚃🚃",
        "kill yourself": "keep yourself safe",
        "Kill yourself": "Keep yourself safe",
        "Kill Yourself": "Keep Yourself Safe",
        "KILL YOURSELF": "KEEP YOURSELF SAFE",
        "faggot": "cute twink",
        "Faggot": "Cute twink",
        "FAGGOT": "CUTE TWINK",
        "NoNewNormal": "NoNewNormal",
        "nonewnormal": "NoNewNormal",
        "NONEWNORMAL": "NONEWNORMAL",
        "nig": "🏀",
        "Nig": "🏀",
        "NIG": "🏀",
    }

    result = create_replace_map()

    assert_that(result).is_equal_to(expected)


@patch("files.helpers.word_censor.REPLACE_MAP", {'retard': 'r-slur', 'Faggot': 'Cute twink', 'NIG': '🏀'})
def test_sub_matcher():
    regex = re.compile(r"(?i)(\s|>)(kill yourself|retard)|(kill yourself|retard)(\s|<)|(\s|>)(nig|faggot)(\s|<)")

    match = regex.search("<p>retard</p>")
    assert_that(sub_matcher(match)).is_equal_to(">r-slur")

    match = regex.search("<p>noretard</p>")
    assert_that(sub_matcher(match)).is_equal_to("r-slur<")

    match = regex.search("<p>ReTaRdEd</p>")
    assert_that(sub_matcher(match)).is_equal_to(">r-slur")

    match = regex.search("<p>NIG</p>")
    assert_that(sub_matcher(match)).is_equal_to(">🏀<")

    match = regex.search("<p>Faggot </p>")
    assert_that(sub_matcher(match)).is_equal_to(">Cute twink ")


@patch("files.helpers.word_censor.SLURS", {
    'retard': 'r-slur',
    'manlet': 'little king',
    ' nig ': '🏀',
    'i hate Carp': 'i love Carp',
    'kike': 'https://sciencedirect.com/science/article/abs/pii/S016028960600033X'
})
def test_censor_slurs():
    word_censor.REPLACE_MAP = create_replace_map()
    word_censor.SLUR_REGEX = create_slur_regex()

    assert_that(censor_slurs("<p>retard</p>", None)).is_equal_to("<p>r-slur</p>")
    assert_that(censor_slurs("<p>preretard</p>", None)).is_equal_to("<p>prer-slur</p>")
    assert_that(censor_slurs("that is Retarded like", None)).is_equal_to("that is R-slured like")
    assert_that(censor_slurs("that is SUPERRETARD like", None)).is_equal_to("that is SUPERR-SLUR like")
    assert_that(censor_slurs('... ReTaRd ...', None)).is_equal_to('... r-slur ...')
    assert_that(censor_slurs("<p>Manlets get out!</p>", None)).is_equal_to("<p>Little kings get out!</p>")

    assert_that(censor_slurs('... "retard" ...', None)).is_equal_to('... "retard" ...')
    assert_that(censor_slurs('... xretardx ...', None)).is_equal_to('... xretardx ...')

    assert_that(censor_slurs("LLM is a manlet hehe", None)).is_equal_to("LLM is a little king hehe")
    assert_that(censor_slurs("LLM is :marseycapitalistmanlet: hehe", None)) \
        .is_equal_to("LLM is :marseycapitalistmanlet: hehe")

    assert_that(censor_slurs('... Nig ...', None)).is_equal_to('... 🏀 ...')
    assert_that(censor_slurs('<p>NIG</p>', None)).is_equal_to('<p>🏀</p>')
    assert_that(censor_slurs('... nigeria ...', None)).is_equal_to('... nigeria ...')

    assert_that(censor_slurs('... i hate Carp ...', None)).is_equal_to('... i love Carp ...')
    assert_that(censor_slurs('... i hate carp ...', None)).is_equal_to('... i love Carp ...')
    assert_that(censor_slurs('... I hate Carp ...', None)).is_equal_to('... I love Carp ...')
    assert_that(censor_slurs('... I Hate Carp ...', None)).is_equal_to('... I Love Carp ...')
    assert_that(censor_slurs('... I HATE CARP ...', None)).is_equal_to('... I LOVE CARP ...')
    assert_that(censor_slurs('... I Hate carp ...', None)).is_equal_to('... i love Carp ...')
    assert_that(censor_slurs('... i Hate Carp ...', None)).is_equal_to('... i love Carp ...')
    assert_that(censor_slurs('... i Hate carp ...', None)).is_equal_to('... i love Carp ...')

    assert_that(censor_slurs('... i hate a carp ...', None)).is_equal_to('... i hate a carp ...')

    assert_that(censor_slurs("<p>retarded SuperManlet NIG</p>", None)) \
        .is_equal_to("<p>r-slured SuperLittle king 🏀</p>")

    assert_that(censor_slurs('... kike ...', None)) \
        .is_equal_to('... https://sciencedirect.com/science/article/abs/pii/S016028960600033X ...')
    assert_that(censor_slurs('... Kike ...', None)) \
        .is_equal_to('... https://sciencedirect.com/science/article/abs/pii/S016028960600033X ...')
    assert_that(censor_slurs('... KIKE ...', None)) \
        .is_equal_to('... https://sciencedirect.com/science/article/abs/pii/S016028960600033X ...')


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
