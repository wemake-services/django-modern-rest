import re
from typing import Final

#: Tokens that can change the group nesting inside a regex pattern.
#: Escaped characters and character classes are matched to be skipped:
#: `\(` and `[(]` do not open any groups.
_GROUP_TOKENS: Final = re.compile(
    r"""
    \\. |                                # escaped char, like `\(`
    \[ \^? \]? (?: [^\]\\] | \\. )* \] | # char class, like `[^\]]`
    \(\?P<(?P<name>\w+)> |               # named group, like `(?P<year>`
    \( |                                 # any other group start
    \)                                   # group end
    """,
    re.VERBOSE | re.DOTALL,
)


def parse_named_groups(source: str) -> dict[str, str]:
    r"""
    Parse sub-patterns of all named groups in a regex pattern.

    We only look at the group nesting, everything that cannot open
    or close a group is skipped: like ``(`` in ``\(`` and in ``[(]``.
    Unmatched ``)`` tokens are ignored, they can only happen
    in patterns we don't fully understand, like verbose mode comments.

    Args:
        source: Regex pattern source, like ``r'^(?P<year>\d{4})/$'``.

    Returns:
        Named groups with their sub-patterns, like ``{'year': r'\d{4}'}``.

    """
    named_groups: dict[str, str] = {}
    opened_groups: list[re.Match[str]] = []
    for token in _GROUP_TOKENS.finditer(source):
        if token.group().startswith('('):
            opened_groups.append(token)
        elif token.group() == ')' and opened_groups:
            named_groups.update(
                _closed_named_group(source, opened_groups.pop(), token),
            )
    return named_groups


def _closed_named_group(
    source: str,
    opened: re.Match[str],
    closed: re.Match[str],
) -> dict[str, str]:
    group_name = opened.group('name')
    if group_name is None:  # unnamed group, like `(\d+)`
        return {}
    return {group_name: source[opened.end() : closed.start()]}
