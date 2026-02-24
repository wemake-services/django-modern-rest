from collections.abc import Callable
from typing import Any
from xml.parsers import expat

import xmltodict
from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import RequestSerializationError
from dmr.parsers import DeserializeFunc, Parser, Raw
from dmr.renderers import Renderer


class XmlParser(Parser):
    """
    Simple XML parser used for testing purposes.

    Converts XML request bodies into Python data structures using
    xmltodict. Not intended for production use.
    """

    __slots__ = ()

    content_type = 'application/xml'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        try:
            return xmltodict.parse(
                to_deserialize,
                process_namespaces=True,
                # TODO: this is very bad :(
                force_list={'detail', 'loc'},
            )
        except expat.ExpatError as exc:
            if to_deserialize == b'':
                return {}
            raise RequestSerializationError(str(exc)) from None


class XmlRenderer(Renderer):
    """
    Simple XML renderer used for testing purposes.

    Serializes Python data structures into XML using xmltodict.
    Not intended for production use.
    """

    __slots__ = ()

    content_type = 'application/xml'

    @override
    def render(
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any],
    ) -> bytes:
        raw_data = xmltodict.unparse(to_serialize, pretty=True)
        assert isinstance(raw_data, str)
        return raw_data.encode('utf8')

    @property
    @override
    def validation_parser(self) -> XmlParser:
        return XmlParser()
