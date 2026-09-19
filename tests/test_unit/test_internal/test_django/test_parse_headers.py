import pytest
from django.utils.datastructures import CaseInsensitiveMapping

from dmr.internal.django import parse_headers


@pytest.mark.parametrize(
    ('header_value', 'expected'),
    [
        ('first,second', ['first', 'second']),
        ('first, second', ['first', 'second']),
        ('first ,second', ['first', 'second']),
        ('first  ,  second', ['first', 'second']),
        ('first,\tsecond', ['first', 'second']),
        (' first , second ', ['first', 'second']),
        ('first,', ['first', '']),
        ('first', ['first']),
    ],
)
def test_parse_headers_split_commas(
    *,
    header_value: str,
    expected: list[str],
) -> None:
    """Optional whitespace around ``','`` is not a part of the values."""
    parsed = parse_headers(
        CaseInsensitiveMapping({'X-Tag': header_value}),
        split_commas=frozenset(('x-tag',)),
    )

    assert parsed['x-tag'] == expected


def test_parse_headers_other_headers_untouched() -> None:
    """Headers outside of *split_commas* keep their raw value."""
    parsed = parse_headers(
        CaseInsensitiveMapping({'X-Other': 'first, second'}),
        split_commas=frozenset(('x-tag',)),
    )

    assert parsed['x-other'] == 'first, second'
