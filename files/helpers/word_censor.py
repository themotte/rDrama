from collections import ChainMap
import re
from re import Match
from typing import Dict, Pattern

from files.helpers.const import SLURS


def first_upper(phrase: str) -> str:
    """Converts the first character of the phrase to uppercase, not messing with the others"""
    return phrase[0].upper() + phrase[1:]


def first_all_upper(phrase: str) -> str:
    """Converts the first character of each word to uppercase, not messing with the others"""
    if " " not in phrase:
        return first_upper(phrase)

    return " ".join([first_upper(word) for word in phrase.split(" ")])


def get_permutations_slur(slur: str, replacer: str = "_") -> Dict[str, str]:
    """
    Given a slur and a replacer, it generates all the possible permutation on the original text and assigns them to the
    corresponding substitution with case
    """
    stripped = slur.strip()
    is_link = replacer.startswith("http")  # special case for the :marseymerchant:

    # the order the things are added into the dict is important, so that the 'Correctest' version is written last
    result = {
        stripped.upper(): replacer.upper() if not is_link else replacer,
        first_all_upper(stripped): first_all_upper(replacer) if not is_link else replacer,
        stripped.lower(): replacer,
        stripped: replacer,
        first_upper(stripped): first_upper(replacer) if not is_link else replacer,
    }

    return result


def create_slur_regex() -> Pattern[str]:
    """Creates the regex that will find the slurs"""
    single_words = "|".join([slur.lower() for slur in SLURS.keys()])

    return re.compile(rf"(?i)(?<=\s|>)({single_words})([\s<,.])")


def create_replace_map() -> Dict[str, str]:
    """Creates the map that will be used to get the matching replaced for the given slur"""
    dicts = [get_permutations_slur(slur, replacer) for (slur, replacer) in SLURS.items()]

    # flattens the list of dict to a single dict
    return dict(ChainMap(*dicts))


SLUR_REGEX = create_slur_regex()
REPLACE_MAP = create_replace_map()


def sub_matcher(match: Match) -> str:
    """given a match returns the correct replacer string"""
    found = match.group(1)
    # if it does not find the correct capitalization, it tries the all lower, or return the original word
    return (REPLACE_MAP.get(found) or REPLACE_MAP.get(found.lower()) or found) + match.group(2)


def censor_slurs(body: str, logged_user) -> str:
    """Censors all the slurs in the body if the user is not logged-in or if they have the slurreplacer active"""

    if not logged_user or logged_user.slurreplacer:
        try:
            body = SLUR_REGEX.sub(sub_matcher, body)
        except Exception as e:
            print(e)

    return body
