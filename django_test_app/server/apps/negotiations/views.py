from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any, TypeAlias, final
from xml.parsers import expat

import pydantic
import xmltodict
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from typing_extensions import override

from django_modern_rest import Body, Controller, ResponseSpec, validate
from django_modern_rest.exceptions import (
    InternalServerError,
    RequestSerializationError,
)
from django_modern_rest.negotiation import ContentType, conditional_type
from django_modern_rest.parsers import DeserializeFunc, Parser, Raw
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.renderers import Renderer

# Used for different test setups:
try:  # pragma: no cover
    from django_modern_rest.plugins.msgspec import (
        MsgspecJsonParser as JsonParser,
    )
except ImportError:  # pragma: no cover
    from django_modern_rest.parsers import (  # type: ignore[assignment]
        JsonParser,
    )

try:  # pragma: no cover
    from django_modern_rest.plugins.msgspec import (
        MsgspecJsonRenderer as JsonRenderer,
    )
except ImportError:  # pragma: no cover
    from django_modern_rest.renderers import (  # type: ignore[assignment]
        JsonRenderer,
    )

_CallableAny: TypeAlias = Callable[..., Any]


# NOTE: this is a overly-simplified example of xml parsing / rendering.
# You *will* need more work.
@final
class XmlParser(Parser):
    __slots__ = ()

    content_type = 'application/xml'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
    ) -> Any:
        try:
            return xmltodict.parse(to_deserialize, process_namespaces=True)
        except expat.ExpatError as exc:
            raise RequestSerializationError(str(exc)) from None


@final
class XmlRenderer(Renderer):
    __slots__ = ()

    content_type = 'application/xml'

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
        assert isinstance(raw_data, str)  # noqa: S101
        return raw_data.encode('utf8')

    @property
    @override
    def validation_parser(self) -> XmlParser:
        return XmlParser()

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


@final
class _RequestModel(pydantic.BaseModel):
    root: dict[str, str]


@final
@method_decorator(csrf_exempt, name='dispatch')
class ContentNegotiationController(
    Controller[PydanticSerializer],
    Body[_RequestModel],
):
    parsers = (JsonParser(), XmlParser())
    renderers = (JsonRenderer(), XmlRenderer())

    def post(
        self,
    ) -> Annotated[
        dict[str, str] | list[str],
        conditional_type({
            ContentType.json: list[str],
            ContentType.xml: dict[str, str],
        }),
    ]:
        if self.request.accepts(ContentType.json):
            return list(self.parsed_body.root.values())
        return self.parsed_body.root

    @validate(
        ResponseSpec(
            return_type=Annotated[
                dict[str, str] | list[str],
                conditional_type({
                    ContentType.json: list[str],
                    ContentType.xml: dict[str, str],
                }),
            ],
            status_code=HTTPStatus.CREATED,
        ),
    )
    def put(self) -> HttpResponse:
        if self.request.accepts(ContentType.json):
            return self.to_response(
                list(self.parsed_body.root.values()),
                status_code=HTTPStatus.CREATED,
            )
        return self.to_response(
            self.parsed_body.root,
            status_code=HTTPStatus.CREATED,
        )
