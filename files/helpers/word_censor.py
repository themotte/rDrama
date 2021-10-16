from collections import ChainMap
import re
from re import Match

from files.helpers.const import SLURS


def create_replace_map():
    dicts = [{
        slur: replacer,
        slur.title(): replacer.title(),
        slur.capitalize(): replacer.capitalize(),
        slur.upper(): replacer.upper(),
    } for (slur, replacer) in SLURS.items()]

    # flattens the list of dict to a single dict
    return dict(ChainMap(*dicts))


REPLACE_MAP = create_replace_map()


def create_variations_slur_regex(slur: str):
    variations = [slur, slur.upper(), slur.capitalize()]

    # capitalize multiple words if there are multiple words (just in case)
    if " " in slur:
        variations.append(slur.title())

    return [rf"(\s|>)({var})|({var})(\s|<)" for var in variations]


def sub_matcher(match: Match):
    found = match.group(2) if (match.group(2) is not None) else match.group(3)
    replacer = REPLACE_MAP[found]
    return (match.group(1) or '') + replacer + (match.group(4) or '')


def censor_slurs(v, body):
    for (slur, replace) in SLURS.items():
        for variation in create_variations_slur_regex(slur):
            try:
                body = re.sub(variation, sub_matcher, body)
            except:
                pass

    return body
