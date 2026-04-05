from typing import Any

import pytest
from django.utils.datastructures import MultiValueDict

from dmr.internal.django import convert_multi_value_dict


@pytest.mark.parametrize(
    ('to_parse', 'force_list', 'cast_null', 'split_commas', 'expected'),
    [
        (
            MultiValueDict(),
            frozenset(),
            frozenset(),
            None,
            {},
        ),
        (
            MultiValueDict(),
            frozenset(),
            frozenset(),
            frozenset(),
            {},
        ),
        (
            MultiValueDict(),
            frozenset(('name',)),
            frozenset(('name',)),
            frozenset(('name',)),
            {},
        ),
        (
            MultiValueDict({'name': ['a', 'b'], 'empty': []}),
            frozenset(),
            frozenset(),
            frozenset(),
            {'name': 'b', 'empty': []},
        ),
        (
            MultiValueDict({'name': ['a', 'b'], 'other': [], 'single': [1]}),  # type: ignore[arg-type]
            frozenset(('name',)),
            frozenset(),
            frozenset(),
            {'name': ['a', 'b'], 'other': [], 'single': 1},
        ),
        (
            MultiValueDict({'name': ['a', 'b'], 'other': [], 'single': [1]}),  # type: ignore[arg-type]
            frozenset(('name', 'other', 'single')),
            frozenset(),
            frozenset(),
            {'name': ['a', 'b'], 'other': [], 'single': [1]},
        ),
        (
            MultiValueDict({'name': ['null'], 'other': ['null']}),
            frozenset(),
            frozenset(('name',)),
            frozenset(),
            {'name': None, 'other': 'null'},
        ),
        (
            MultiValueDict({'name': ['a', 'b', 'null']}),
            frozenset(('name', 'other')),
            frozenset(('name', 'other')),
            frozenset(),
            {'name': ['a', 'b', None]},
        ),
        (
            MultiValueDict({'name': ['1,2,3,4,5'], 'other': ['6,7']}),
            frozenset(),
            frozenset(),
            frozenset(('name',)),
            {'name': ['1', '2', '3', '4', '5'], 'other': '6,7'},
        ),
        (
            MultiValueDict({'name': ['1,2,3,4,5'], 'other': ['6,7']}),
            frozenset(),
            frozenset(('name',)),
            frozenset(('name', 'missing')),
            {'name': ['1', '2', '3', '4', '5'], 'other': '6,7'},
        ),
        (
            MultiValueDict({'name': ['1,2,3,4,5'], 'other': ['6,7']}),
            frozenset(('name',)),
            frozenset(),
            frozenset(('name',)),
            {'name': ['1,2,3,4,5'], 'other': '6,7'},
        ),
    ],
)
def test_convert_multi_value_dict(
    *,
    to_parse: 'MultiValueDict[str, Any]',
    force_list: frozenset[str],
    cast_null: frozenset[str],
    split_commas: frozenset[str] | None,
    expected: dict[str, Any],
) -> None:
    """Test multivalue dict works correctly."""
    assert (
        convert_multi_value_dict(
            to_parse,
            force_list=force_list,
            cast_null=cast_null,
            split_commas=split_commas,
        )
        == expected
    )
