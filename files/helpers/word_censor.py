from collections import ChainMap
import re
from re import Match
from typing import List, Dict

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


def create_replace_map() -> Dict[str, str]:
    """Creates the map that will be used to get the mathing replaced for the given slur"""
    dicts = [get_permutations_slur(slur, replacer) for (slur, replacer) in SLURS.items()]

    # flattens the list of dict to a single dict
    return dict(ChainMap(*dicts))


REPLACE_MAP = create_replace_map()


def create_variations_slur_regex(slur: str) -> List[str]:
    """For a given match generates the corresponding replacer"""
    permutations = get_permutations_slur(slur)

    if slur.startswith(" ") and slur.endswith(" "):
        return [rf"(\s|>)({perm})(\s|<)" for perm in permutations.keys()]
    else:
        return [rf"(\s|>)({perm})|({perm})(\s|<)" for perm in permutations.keys()]


def sub_matcher(match: Match) -> str:
    # special case when it should match exact word
    if len(match.groups()) == 3:
        found = match.group(2)
        replacer = REPLACE_MAP[found]
        return match.group(1) + replacer + match.group(3)

    else:  # normal case with prefix or suffix
        found = match.group(2) if (match.group(2) is not None) else match.group(3)
        replacer = REPLACE_MAP[found]
        return (match.group(1) or '') + replacer + (match.group(4) or '')


def censor_slurs(body: str, logged_user) -> str:
    if logged_user and not logged_user.slurreplacer:
        return body

    for (slur, replace) in SLURS.items():
        for variation in create_variations_slur_regex(slur):
            try:
                body = re.sub(variation, sub_matcher, body)
            except Exception as e:
                print(e)

    return body
