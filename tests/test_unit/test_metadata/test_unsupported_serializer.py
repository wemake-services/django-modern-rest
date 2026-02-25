import pytest
from typing_extensions import override

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.negotiation import ContentType
from dmr.parsers import Parser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from tests.infra.xml_format import XmlParser


class _JsonPydanticSerializer(PydanticSerializer):
    @override
    @classmethod
    def is_supported(cls, pluggable: Parser | Renderer) -> bool:
        return pluggable.content_type == ContentType.json


def test_unsupported_serializer_thing() -> None:
    """Ensures that it is impossible to construct an unsupported object."""
    with pytest.raises(EndpointMetadataError, match='XmlParser'):

        class _Controller(Controller[_JsonPydanticSerializer]):
            parsers = (XmlParser(),)

            def get(self) -> str:
                raise NotImplementedError
