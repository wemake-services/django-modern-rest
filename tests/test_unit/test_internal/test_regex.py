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
        # Escaped and quantified parens do not open or close groups:
        (r'^(?P<price>\d+\(\$\))$', {'price': r'\d+\(\$\)'}),
        (r'^(?P<call>[()]+)$', {'call': '[()]+'}),
        (r'^(?P<bracket>[^]]+)$', {'bracket': '[^]]+'}),
        # Nested groups:
        (
            r'^(?P<date>(?P<year>\d{4})-(\d{2}))$',
            {'date': r'(?P<year>\d{4})-(\d{2})', 'year': r'\d{4}'},
        ),
        # Comments are balanced, so they are parsed correctly:
        (r'^(?#some comment)(?P<id>\d+)$', {'id': r'\d+'}),
        # Unmatched `)` inside a verbose mode comment is ignored:
        ('(?x) [a-z]  # ) \n (?P<id>[0-9]+)', {'id': '[0-9]+'}),
    ],
)
def test_parse_named_groups(
    source: str,
    named_groups: dict[str, str],
) -> None:
    """Ensure that named groups are parsed with their sub-patterns."""
    assert parse_named_groups(source) == named_groups
    # All named groups that `re` knows about must be found:
    assert set(re.compile(source).groupindex) == set(named_groups)
