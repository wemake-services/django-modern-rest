from collections.abc import Callable
from typing import Any, final
from xml.parsers import expat

import xmltodict_rs as xmltodict
from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import (
    InternalServerError,
    RequestSerializationError,
)
from dmr.parsers import DeserializeFunc, Parser, Raw
from dmr.renderers import Renderer


@final
class XmlParser(Parser):
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
            parsed = xmltodict.parse(
                to_deserialize,
                process_namespaces=True,
                postprocessor=self._postprocessor,
                # TODO: this is really bad, but I have no idea what to do.
                force_list={'detail', 'loc'},
            )
        except expat.ExpatError as exc:
            raise RequestSerializationError(str(exc)) from None
        return parsed[next(iter(parsed.keys()))]

    def _postprocessor(
        self,
        path: Any,
        key: str,
        xml_value: Any,
    ) -> tuple[str, Any]:
        # xmltodict converts empty tags to `None`; for leaf fields in payloads
        # we normalize them to empty strings to match OpenAPI string semantics.
        if xml_value is None:
            return key, ''
        return key, xml_value


@final
class XmlRenderer(Renderer):
    __slots__ = ()

    content_type = 'application/xml'

    @override
    def render(
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any],
    ) -> bytes:
        preprocessor = self._wrap_serializer(serializer_hook)
        raw_data = xmltodict.unparse(
            {type(to_serialize).__qualname__: to_serialize},
            preprocessor=preprocessor,
        )
        assert isinstance(raw_data, str)
        return raw_data.encode('utf8')

    @property
    @override
    def validation_parser(self) -> XmlParser:
        return XmlParser()

    def _wrap_serializer(
        self,
        serializer_hook: Callable[[Any], Any],
    ) -> Callable[[str, Any], tuple[str, Any]]:
        def factory(xml_key: str, xml_value: Any) -> tuple[str, Any]:
            try:  # noqa: SIM105
                xml_value = serializer_hook(xml_value)
            except InternalServerError:
                pass  # noqa: WPS420
            return xml_key, xml_value

        return factory
