import pytest
from typing_extensions import override

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.metadata import EndpointMetadata
from dmr.negotiation import ContentType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from tests.infra.xml_format import XmlParser


class _JsonPydanticSerializer(PydanticSerializer):
    @override
    @classmethod
    def validate(
        cls,
        controller_cls: type[Controller[BaseSerializer]],
        metadata: EndpointMetadata,
    ) -> None:
        super().validate(controller_cls, metadata)
        for parser in metadata.parsers.values():
            if parser.content_type != ContentType.json:
                raise EndpointMetadataError(f'Unsupported {parser!r}')


def test_unsupported_serializer_thing() -> None:
    """Ensures that it is impossible to construct an unsupported object."""
    with pytest.raises(EndpointMetadataError, match='XmlParser'):

        class _Controller(Controller[_JsonPydanticSerializer]):
            parsers = (XmlParser(),)

            def get(self) -> str:
                raise NotImplementedError


def test_supported_serializer() -> None:
    """Ensures that it is possible to construct a supported object."""
    class _Controller(Controller[_JsonPydanticSerializer]):

        def get(self) -> str:
            raise NotImplementedError
