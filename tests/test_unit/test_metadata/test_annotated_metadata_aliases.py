import json
from typing import Annotated, Any, Final, final

import pydantic
import pytest
from django.urls import path
from inline_snapshot import snapshot
from typing_extensions import TypeAliasType

from dmr import Body, Controller, Query
from dmr.components import BodyComponent, ComponentParser
from dmr.internal.dataclass_aliases import Field, FieldInfo
from dmr.internal.negotiation import ConditionalType, get_conditional_types
from dmr.metadata import ResponseSpecMetadata, get_annotated_metadata
from dmr.negotiation import ContentType, conditional_type
from dmr.openapi import build_schema
from dmr.openapi.objects import MediaTypeMetadata, ParameterMetadata
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router

# Type checkers only allow `TypeAliasType` to build real type aliases,
# these tests build them dynamically instead:
_alias_factory: Any = TypeAliasType


@final
class _Model(pydantic.BaseModel):
    search: str


_CONDITIONAL: Final = conditional_type({
    ContentType.json: _Model,
    ContentType.msgpack: str,
})

# `Annotated` caches its arguments, so equal metadata objects collapse
# into one. We reuse the very same instances to keep `is` checks honest:
_NOT_MERGEABLE: Final = (
    (ParameterMetadata, ParameterMetadata(description='aliased')),
    (MediaTypeMetadata, MediaTypeMetadata(example='aliased')),
    (ConditionalType, _CONDITIONAL),
    (FieldInfo, Field(alias='aliased')),
    (ComponentParser, BodyComponent()),
)
_ALL_METADATA: Final = (
    *_NOT_MERGEABLE,
    (ResponseSpecMetadata, ResponseSpecMetadata()),
)


@pytest.mark.parametrize(('metadata_type', 'metadata'), _ALL_METADATA)
def test_metadata_behind_type_alias(
    *,
    metadata_type: type[Any],
    metadata: Any,
) -> None:
    """Ensures every metadata type we look up is found behind an alias."""
    aliased = _alias_factory('aliased', Annotated[_Model, metadata])
    nested = _alias_factory('nested', aliased)

    assert get_annotated_metadata(aliased, metadata_type) is metadata
    assert get_annotated_metadata(nested, metadata_type) is metadata


@pytest.mark.parametrize(('metadata_type', 'metadata'), _NOT_MERGEABLE)
def test_metadata_is_not_taken_from_union_members(
    *,
    metadata_type: type[Any],
    metadata: Any,
) -> None:
    """Ensures that only mergeable metadata is collected from unions."""
    union = Annotated[_Model, metadata] | str

    assert get_annotated_metadata(union, metadata_type) is None


def test_model_meta_is_still_used() -> None:
    """Ensures that separately passed ``__metadata__`` still works."""
    metadata = ParameterMetadata(description='from model_meta')

    assert (
        get_annotated_metadata(
            _Model,
            ParameterMetadata,
            model_meta=(metadata,),
        )
        is metadata
    )


_AliasedConditional = TypeAliasType(
    '_AliasedConditional',
    Annotated[_Model, _CONDITIONAL],
)


def test_conditional_types_behind_alias() -> None:
    """Ensures that conditional types survive a type alias."""
    assert get_conditional_types(_AliasedConditional, ()) == {
        ContentType.json: _Model,
        ContentType.msgpack: str,
    }


_AliasedQuery = TypeAliasType(
    '_AliasedQuery',
    Annotated[_Model, ParameterMetadata(description='Aliased query')],
)
_AliasedBody = TypeAliasType(
    '_AliasedBody',
    Annotated[_Model, MediaTypeMetadata(example={'search': 'aliased'})],
)


@final
class _AliasedMetadataController(Controller[PydanticSerializer]):
    def post(
        self,
        parsed_query: Query[_AliasedQuery],
        parsed_body: Body[_AliasedBody],
    ) -> str:
        raise NotImplementedError


def test_aliased_metadata_reaches_openapi() -> None:
    """Ensures aliased metadata is not lost in the OpenAPI schema."""
    schema = json.loads(
        json.dumps(
            build_schema(
                Router(
                    'api/',
                    [path('aliased/', _AliasedMetadataController.as_view())],
                ),
            ).convert(),
        ),
    )
    operation = schema['paths']['/api/aliased/']['post']

    assert [
        (parameter['name'], parameter['description'])
        for parameter in operation['parameters']
    ] == snapshot([('search', 'Aliased query')])
    assert operation['requestBody']['content']['application/json'][
        'example'
    ] == snapshot({'search': 'aliased'})
