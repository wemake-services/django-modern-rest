import pytest

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import (
    PydanticFastSerializer,
)
from tests.infra.xml_format import XmlParser, XmlRenderer


def test_pydantic_fast_non_json() -> None:
    """Ensures that fast serializer only supports json."""
    with pytest.raises(
        EndpointMetadataError,
        match='serializer does not support',
    ):

        class _RendererController(
            Controller[PydanticFastSerializer],
        ):
            renderers = (XmlRenderer(),)

            def get(self) -> str:
                raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match='serializer does not support',
    ):

        class _ParserController(
            Controller[PydanticFastSerializer],
        ):
            parsers = (XmlParser(),)

            def get(self) -> str:
                raise NotImplementedError
