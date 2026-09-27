import pytest

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.serializer import ContextField


class _Model(msgspec.Struct, frozen=True):
    name: str = 'default'


def test_struct_without_defaults() -> None:
    """Ensures that a `Struct` without gc is built."""
    context_model = MsgspecSerializer.build_context_model(
        'Context',
        {'parsed_body': ContextField(_Model)},
    )

    assert issubclass(context_model.model, msgspec.Struct)
    assert context_model.model.__struct_config__.gc is False
    assert context_model.to_kwargs is not None
    assert context_model.to_kwargs(
        MsgspecSerializer.from_python(
            {'parsed_body': {'name': 'test'}},
            context_model.model,
            strict=None,
        ),
    ) == {'parsed_body': _Model(name='test')}


def test_struct_with_defaults() -> None:
    """Ensures that defaults are supported by the `Struct`."""
    default = _Model()
    context_model = MsgspecSerializer.build_context_model(
        'Context',
        {
            # Defaults go first on purpose, we must reorder them:
            'parsed_query': ContextField(_Model | None, None),
            'parsed_headers': ContextField(_Model, default),
            'parsed_body': ContextField(_Model),
        },
    )

    assert context_model.model.__struct_fields__ == (
        'parsed_body',
        'parsed_query',
        'parsed_headers',
    )
    assert context_model.to_kwargs is not None
    parsed = context_model.to_kwargs(
        MsgspecSerializer.from_python(
            {'parsed_body': {'name': 'test'}},
            context_model.model,
            strict=None,
        ),
    )
    assert parsed == {
        'parsed_body': _Model(name='test'),
        'parsed_query': None,
        'parsed_headers': default,
    }
    # Defaults are not copied:
    assert parsed['parsed_headers'] is default
