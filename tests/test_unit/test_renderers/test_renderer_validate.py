import pytest
from typing_extensions import override

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.metadata import EndpointMetadata
from dmr.parsers import Parser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer


class _StrictRenderer(Renderer):
    """Renderer that only works with GET endpoints."""

    content_type = 'application/strict'

    @override
    def render(self, to_serialize, serializer_hook):
        raise NotImplementedError

    @property
    @override
    def validation_parser(self) -> Parser:
        raise NotImplementedError

    @override
    def validate(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        metadata: EndpointMetadata,
    ) -> None:
        """Only allow this renderer on GET endpoints."""
        if metadata.method != 'get':
            raise EndpointMetadataError(
                f'{type(self).__name__} only works on get endpoints, '
                f'found: {metadata.method}',
            )


def test_custom_renderer_validate_pass() -> None:
    """Renderer.validate passes when constraints are met."""

    class _Controller(Controller[PydanticSerializer]):
        renderers = (_StrictRenderer(),)

        def get(self) -> list[dict[str, str]]:
            raise NotImplementedError

    # Controller is created successfully at import time.


def test_custom_renderer_validate_fail() -> None:
    """Renderer.validate raises on invalid usage."""
    with pytest.raises(EndpointMetadataError, match='only works on get'):

        class _Controller(Controller[PydanticSerializer]):
            renderers = (_StrictRenderer(),)

            def post(self, parsed_body: dict[str, str]) -> dict[str, str]:
                raise NotImplementedError
