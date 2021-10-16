from collections import ChainMap
import re
from re import Match

from files.helpers.const import SLURS


def create_replace_map():
    dicts = [{
        slur.strip(): replacer,
        slur.strip().title(): replacer.title(),
        slur.strip().capitalize(): replacer.capitalize(),
        slur.strip().upper(): replacer.upper(),
    } for (slur, replacer) in SLURS.items()]

    # flattens the list of dict to a single dict
    return dict(ChainMap(*dicts))


REPLACE_MAP = create_replace_map()


def create_variations_slur_regex(slur: str):
    stripped = slur.strip()
    variations = [stripped, stripped.upper(), stripped.capitalize()]

    # capitalize multiple words if there are multiple words (just in case)
    if " " in stripped:
        variations.append(stripped.title())

    if slur.startswith(" ") and slur.endswith(" "):
        return [rf"(\s|>)({var})(\s|<)" for var in variations]
    else:
        return [rf"(\s|>)({var})|({var})(\s|<)" for var in variations]


def sub_matcher(match: Match):
    # special case when it should match exact word
    if len(match.groups()) is 3:
        found = match.group(2)
        replacer = REPLACE_MAP[found]
        return match.group(1) + replacer + match.group(3)

    else:  # normal case with prefix or suffix
        found = match.group(2) if (match.group(2) is not None) else match.group(3)
        replacer = REPLACE_MAP[found]
        return (match.group(1) or '') + replacer + (match.group(4) or '')


def censor_slurs(v, body: str):
    if v and not v.slurreplacer:
        return body

    for (slur, replace) in SLURS.items():
        for variation in create_variations_slur_regex(slur):
            try:
                body = re.sub(variation, sub_matcher, body)
            except Exception as e:
                print(e)

    return body
