import dataclasses

import pydantic
from typing_extensions import is_typeddict

from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import ContextField


class _Model(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    name: str = 'default'


def test_typed_dict_without_defaults() -> None:
    """Ensures that `TypedDict` is used when there are no defaults."""
    context_model = PydanticSerializer.build_context_model(
        'Context',
        {'parsed_body': ContextField(_Model)},
    )

    assert is_typeddict(context_model.model)
    assert context_model.to_kwargs is None
    assert PydanticSerializer.from_python(
        {'parsed_body': {'name': 'test'}},
        context_model.model,
        strict=None,
    ) == {'parsed_body': _Model(name='test')}


def test_dataclass_with_defaults() -> None:
    """Ensures that a dataclass is used when there are defaults."""
    default = _Model()
    context_model = PydanticSerializer.build_context_model(
        'Context',
        {
            # Defaults go first on purpose, we must reorder them:
            'parsed_query': ContextField(_Model | None, None),
            'parsed_headers': ContextField(_Model, default),
            'parsed_body': ContextField(_Model),
        },
    )

    assert dataclasses.is_dataclass(context_model.model)
    assert [
        field.name for field in dataclasses.fields(context_model.model)
    ] == ['parsed_body', 'parsed_query', 'parsed_headers']
    assert context_model.to_kwargs is not None
    parsed = context_model.to_kwargs(
        PydanticSerializer.from_python(
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
