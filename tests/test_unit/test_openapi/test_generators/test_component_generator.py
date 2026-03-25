import re
from typing import Annotated, Any, Generic, TypeAlias, TypeVar

import pytest
from django.urls import path
from typing_extensions import override

from dmr import Controller
from dmr.components import ComponentParser
from dmr.endpoint import Endpoint
from dmr.metadata import EndpointMetadata
from dmr.openapi.core.context import OpenAPIContext
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer

_FakeT = TypeVar('_FakeT')


class _FakeComponent(ComponentParser, Generic[_FakeT]):
    context_name = 'parsed_fake'

    @override
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        *,
        field_model: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @override
    def get_schema(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
        context: OpenAPIContext,
    ) -> Any:
        """Just return None."""


_Fake: TypeAlias = Annotated[_FakeT, _FakeComponent()]


class _FakeController(Controller[PydanticSerializer]):
    def get(self, parsed_fake: _Fake[int]) -> str:
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
            'unique-operationid',
            path('/', _FakeController.as_view()),
            _FakeController.api_endpoints['GET'].metadata,
            PydanticSerializer,
        )
