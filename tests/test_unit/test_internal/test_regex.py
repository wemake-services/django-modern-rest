import re

import pytest

from dmr.internal.regex import parse_named_groups


@pytest.mark.parametrize(
    ('source', 'named_groups'),
    [
        # No groups at all:
        (r'^articles/$', {}),
        # Unnamed groups are ignored:
        (r'^articles/(\d{4})/$', {}),
        # Regular named groups:
        (r'^v(?P<version>\d+)/$', {'version': r'\d+'}),
        (
            r'^articles/(?P<year>[0-9]{4})/(?P<slug>[\w-]+)/$',
            {'year': '[0-9]{4}', 'slug': r'[\w-]+'},
        ),
        # Top level alternation:
        (r'^(?P<format>json|xml)$', {'format': 'json|xml'}),
        # Escaped parens and parens in a character class
        # do not close the group:
        (r'^(?P<price>\d+\(\$\))$', {'price': r'\d+\(\$\)'}),
        (r'^(?P<call>[()]+)$', {'call': '[()]+'}),
        (r'^(?P<closing>[)]+)$', {'closing': '[)]+'}),
        (r'^(?P<bracket>[^]]+)$', {'bracket': '[^]]+'}),
        # Nested groups:
        (
            r'^(?P<date>(?P<year>\d{4})-(\d{2}))$',
            {'date': r'(?P<year>\d{4})-(\d{2})', 'year': r'\d{4}'},
        ),
        # Comments do not close the group either:
        (r'^(?P<id>(?#some comment)\d+)$', {'id': r'(?#some comment)\d+'}),
        # `(?P<x>` inside a literal is not a group, `re` does not see it too:
        (r'\(?P<x>', {}),
    ],
)
def test_parse_named_groups(
    *,
    source: str,
    named_groups: dict[str, str],
) -> None:
    """Ensure that named groups are parsed with their sub-patterns."""
    assert parse_named_groups(source) == named_groups
    # All named groups that `re` knows about must be found:
    assert set(re.compile(source).groupindex) == set(named_groups)


def test_parse_named_groups_backreference() -> None:
    """Ensure that groups we cannot reuse on their own are skipped."""
    source = r'^(?P<sep>[-_])(?P<same>\1)$'

    # `\1` is not a valid pattern outside of this regex:
    assert parse_named_groups(source) == {'sep': '[-_]'}
    assert set(re.compile(source).groupindex) == {'sep', 'same'}
