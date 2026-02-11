from collections.abc import Callable
from typing import Any, ClassVar
from xml.parsers import expat

import xmltodict
from django.http import HttpRequest
from typing_extensions import override

from django_modern_rest.exceptions import (
    InternalServerError,
    RequestSerializationError,
)
from django_modern_rest.parsers import DeserializeFunc, Parser, Raw
from django_modern_rest.renderers import Renderer


# NOTE: this is a overly-simplified example of xml parsing / rendering.
# You *will* need more work.
class XmlParser(Parser):
    __slots__ = ()

    content_type: ClassVar[str] = 'application/xml'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer: DeserializeFunc | None = None,
        *,
        strict: bool = True,
        request: HttpRequest,
    ) -> Any:
        try:
            return xmltodict.parse(to_deserialize, process_namespaces=True)
        except expat.ExpatError as exc:
            raise RequestSerializationError(str(exc)) from None


class XmlRenderer(Renderer):
    __slots__ = ()

    content_type: ClassVar[str] = 'application/xml'

    @override
    def render(
        self,
        to_serialize: Any,
        serializer: Callable[[Any], Any],
    ) -> bytes:
        preprocessor = self._wrap_serializer(serializer)
        raw_data = xmltodict.unparse(
            preprocessor('', to_serialize)[1],
            preprocessor=preprocessor,
        )
        assert isinstance(raw_data, str)
        return raw_data.encode('utf8')

    def _wrap_serializer(
        self,
        serializer: Callable[[Any], Any],
    ) -> Callable[[str, Any], tuple[str, Any]]:
        def factory(xml_key: str, xml_value: Any) -> tuple[str, Any]:
            try:  # noqa: SIM105
                xml_value = serializer(xml_value)
            except InternalServerError:
                pass  # noqa: WPS420
            return xml_key, xml_value

        return factory
