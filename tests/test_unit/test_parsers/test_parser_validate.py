import pytest
from typing_extensions import override

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.metadata import EndpointMetadata
from dmr.parsers import DeserializeFunc, Parser, Raw
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer


class _StrictParser(Parser):
    """Parser that only works with GET endpoints."""

    content_type = 'application/strict'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: object,
        model: object,
    ) -> None:
        raise NotImplementedError

    @override
    def validate(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        metadata: EndpointMetadata,
    ) -> None:
        """Only allow this parser on GET endpoints."""
        if metadata.method != 'get':
            raise EndpointMetadataError(
                f'{type(self).__name__} only works on get endpoints, '
                f'found: {metadata.method}',
            )


def test_custom_parser_validate_pass() -> None:
    """Parser.validate passes when constraints are met."""

    class _Controller(Controller[PydanticSerializer]):
        parsers = (_StrictParser(),)

        def get(self) -> list[dict[str, str]]:
            raise NotImplementedError


def test_custom_parser_validate_fail() -> None:
    """Parser.validate raises on invalid usage."""
    with pytest.raises(EndpointMetadataError, match='only works on get'):

        class _Controller(Controller[PydanticSerializer]):
            parsers = (_StrictParser(),)

            def post(self, parsed_body: dict[str, str]) -> dict[str, str]:
                raise NotImplementedError
