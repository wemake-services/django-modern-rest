import re
from typing import Any, Generic, TypeVar

import pytest
from typing_extensions import override

from dmr import Blueprint, Controller
from dmr.components import ComponentParser
from dmr.endpoint import Endpoint
from dmr.metadata import EndpointMetadata
from dmr.openapi.core.context import OpenAPIContext
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer

_FakeT = TypeVar('_FakeT')


class _Fake(ComponentParser, Generic[_FakeT]):
    context_name = 'parsed_fake'

    @override
    @classmethod
    def provide_context_data(
        cls,
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
        *,
        field_model: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @override
    @classmethod
    def get_schema(
        cls,
        model: Any,
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
        context: OpenAPIContext,
    ) -> Any:
        """Just return None."""


class _FakeController(
    Controller[PydanticSerializer],
    _Fake[int],
):
    def get(self) -> str:
        raise NotImplementedError


def test_fake_component(openapi_context: OpenAPIContext) -> None:
    """Ensures that wrong components raise."""
    with pytest.raises(
        TypeError,
        match=re.escape(
            "Returning <class 'NoneType'> from ComponentParser.get_schema",
        ),
    ):
        openapi_context.generators.component_parsers(
            _FakeController.api_endpoints['GET'].metadata,
            PydanticSerializer,
        )
