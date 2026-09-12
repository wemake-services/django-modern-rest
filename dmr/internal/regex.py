import re

from django.contrib.admindocs.utils import named_group_matcher


def parse_named_groups(source: str) -> dict[str, str]:
    r"""
    Parse sub-patterns of all named groups in a regex pattern.

    Django has :func:`django.contrib.admindocs.utils.replace_named_groups`,
    but it solves the opposite problem: it throws the sub-patterns away,
    replacing ``(?P<year>\d{4})`` with ``<year>`` to show a readable url.
    We reuse its ``named_group_matcher`` to find where the groups start,
    and :mod:`re` itself to find where they end.

    Args:
        source: Regex pattern source, like ``r'^(?P<year>\d{4})/$'``.

    Returns:
        Named groups with their sub-patterns, like ``{'year': r'\d{4}'}``.
        Groups that make no sense on their own are skipped,
        like ``(?P<repeat>\1)`` with its backreference.

    """
    named_groups: dict[str, str] = {}
    for match in named_group_matcher.finditer(source):
        group_source = _find_group_source(source, match.end())
        if group_source is not None:
            # `named_group_matcher` captures the name in `<>`, like `<year>`:
            group_name = match[1].removeprefix('<').removesuffix('>')
            named_groups[group_name] = group_source
    return named_groups


def _find_group_source(source: str, group_start: int) -> str | None:
    # A group ends at the first `)` that leaves a valid regex behind:
    # any earlier `)` is escaped, is inside a character class,
    # or closes a nested group. All three cut the sub-pattern in a place
    # where `re` refuses to compile it, because `\d+\` is a dangling escape,
    # `[0-9` is an unterminated character set,
    # and `(x|y` is an unterminated group.
    for group_end, char in enumerate(source[group_start:], group_start):
        group_source = source[group_start:group_end]
        if char == ')' and _is_valid_regex(group_source):
            return group_source
    return None


def _is_valid_regex(source: str) -> bool:
    try:
        re.compile(source)
    except re.error:
        return False
    return True
