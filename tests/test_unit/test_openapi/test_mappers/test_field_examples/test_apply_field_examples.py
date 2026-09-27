from types import MappingProxyType
from typing import Any, Final

import pytest

from dmr.openapi.mappers.field_examples import apply_field_examples
from dmr.openapi.objects import OpenAPIType, Reference, Schema
from dmr.types import EMPTY

_PREFIX: Final = '#/components/schemas/'
_COMPONENTS: Final = MappingProxyType({
    'Profile': Schema(
        type=OpenAPIType.OBJECT,
        properties={
            'bio': Schema(type=OpenAPIType.STRING, examples=['Hello']),
            'age': Schema(type=OpenAPIType.INTEGER),
        },
    ),
})
_PROFILE: Final = Reference(ref=f'{_PREFIX}Profile')
_OPTIONAL_PROFILE: Final = Schema(
    any_of=[_PROFILE, Schema(type=OpenAPIType.NULL)],
)


@pytest.mark.parametrize(
    ('schema', 'example', 'expected'),
    [
        # JSON Schema `examples` of a field:
        (
            Schema(properties={'name': Schema(examples=['admin', 'root'])}),
            {'name': 'random'},
            {'name': 'admin'},
        ),
        # OAS `example` of a field:
        (
            Schema(properties={'name': Schema(example='admin')}),
            {'name': 'random'},
            {'name': 'admin'},
        ),
        # `None` is a valid hand-written example:
        (
            Schema(properties={'name': Schema(example=None)}),
            {'name': 'random'},
            {'name': None},
        ),
        # Fields without examples keep generated values:
        (
            Schema(properties={'age': Schema(type=OpenAPIType.INTEGER)}),
            {'age': 1},
            {'age': 1},
        ),
        # Keys that are not in properties are kept:
        (
            Schema(properties={'name': Schema(examples=['admin'])}),
            {'other': 1},
            {'other': 1},
        ),
        # Nested models:
        (
            Schema(properties={'profile': _PROFILE}),
            {'profile': {'bio': 'random', 'age': 1}},
            {'profile': {'bio': 'Hello', 'age': 1}},
        ),
        # References that can't be resolved are kept:
        (
            Schema(properties={'other': Reference(ref=f'{_PREFIX}Missing')}),
            {'other': {'bio': 'random'}},
            {'other': {'bio': 'random'}},
        ),
        # Lists of nested models:
        (
            Schema(properties={'profiles': Schema(items=_PROFILE)}),
            {'profiles': [{'bio': 'first', 'age': 1}, {'bio': 'second'}]},
            {'profiles': [{'bio': 'Hello', 'age': 1}, {'bio': 'Hello'}]},
        ),
        # List items with examples:
        (
            Schema(items=Schema(examples=['tag'])),
            ['first', 'second'],
            ['tag', 'tag'],
        ),
        # `X | None` with a value:
        (
            Schema(properties={'maybe': _OPTIONAL_PROFILE}),
            {'maybe': {'bio': 'random', 'age': 1}},
            {'maybe': {'bio': 'Hello', 'age': 1}},
        ),
        # `X | None` with `None`:
        (
            Schema(properties={'maybe': _OPTIONAL_PROFILE}),
            {'maybe': None},
            {'maybe': None},
        ),
        # We don't know which schema of other unions was generated:
        (
            Schema(
                properties={
                    'either': Schema(
                        one_of=[_PROFILE, Schema(examples=['other'])],
                    ),
                },
            ),
            {'either': {'bio': 'random'}},
            {'either': {'bio': 'random'}},
        ),
        # Examples are not generated:
        (
            Schema(
                any_of=[
                    Schema(examples=['admin']),
                    Schema(type=OpenAPIType.NULL),
                ],
            ),
            EMPTY,
            EMPTY,
        ),
    ],
)
def test_apply_field_examples(
    *,
    schema: Schema,
    example: Any,
    expected: Any,
) -> None:
    """Ensure that hand-written field examples replace generated values."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1639
    assert (
        apply_field_examples(schema, example, _COMPONENTS, _PREFIX) == expected
    )
