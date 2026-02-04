from collections.abc import Callable
from typing import Any, ClassVar

import xmltodict
from typing_extensions import override

from django_modern_rest.exceptions import InternalServerError
from django_modern_rest.parsers import DeserializeFunc, Parser, Raw
from django_modern_rest.renderers import Renderer


# NOTE: this is a overly-simplified example of xml parsing / rendering.
# You *will* need more work.
class XmlParser(Parser):
    __slots__ = ()

    content_type: ClassVar[str] = 'application/xml'

    @override
    @classmethod
    def parse(
        cls,
        to_deserialize: Raw,
        deserializer: DeserializeFunc | None = None,
        *,
        strict: bool = True,
    ) -> Any:
        return xmltodict.parse(to_deserialize, process_namespaces=True)


class XmlRenderer(Renderer):
    __slots__ = ()

    content_type: ClassVar[str] = 'application/xml'

    @override
    @classmethod
    def render(
        cls,
        to_serialize: Any,
        serializer: Callable[[Any], Any],
    ) -> bytes:
        preprocessor = cls._wrap_serializer(serializer)
        raw_data = xmltodict.unparse(
            preprocessor('', to_serialize)[1],
            preprocessor=preprocessor,
        )
        assert isinstance(raw_data, str)
        return raw_data.encode('utf8')

    @classmethod
    def _wrap_serializer(
        cls,
        serializer: Callable[[Any], Any],
    ) -> Callable[[str, Any], tuple[str, Any]]:
        def factory(xml_key: str, xml_value: Any) -> tuple[str, Any]:
            try:  # noqa: SIM105
                xml_value = serializer(xml_value)
            except InternalServerError:
                pass  # noqa: WPS420
            return xml_key, xml_value

        return factory
