from inline_snapshot import snapshot

from dmr.openapi.mappers import KwargMapper
from dmr.openapi.objects.enums import OpenAPIFormat, OpenAPIType
from dmr.openapi.objects.schema import Schema
from dmr.openapi.types import KwargDefinition


def test_kwarg_mapper_call() -> None:
    """Ensure ``KwargMapper`` works."""
    kwarg_def = KwargDefinition(
        title='Test Title',
        description='Test Description',
        default='Test Default',
        format='email',
        schema_extra={'x-extra': 'value'},
    )
    schema = Schema(type=OpenAPIType.STRING)

    assert KwargMapper()(schema, kwarg_def) == {
        'title': 'Test Title',
        'description': 'Test Description',
        'default': 'Test Default',
        'format': OpenAPIFormat.EMAIL,
        'x-extra': 'value',
    }


def test_kwarg_mapper_invalid_format() -> None:
    """Ensure ``KwargMapper`` ignores invalid format."""
    updates = KwargMapper()(
        Schema(type=OpenAPIType.STRING),
        KwargDefinition(format='invalid-format'),
    )

    assert updates == snapshot({'format': 'invalid-format'})
