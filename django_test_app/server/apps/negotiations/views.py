from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any, TypeAlias, final
from xml.parsers import expat

import pydantic
import xmltodict
from django.http import HttpRequest, HttpResponse
from typing_extensions import override

from dmr import Body, Controller, ResponseSpec, validate
from dmr.exceptions import (
    InternalServerError,
    RequestSerializationError,
)
from dmr.internal.schema import get_schema_name
from dmr.negotiation import ContentType, conditional_type
from dmr.parsers import DeserializeFunc, Parser, Raw
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer

# Used for different test setups:
try:  # pragma: no cover
    from dmr.plugins.msgspec import (
        MsgspecJsonParser as JsonParser,
    )
except ImportError:  # pragma: no cover
    from dmr.parsers import (  # type: ignore[assignment]
        JsonParser,
    )

try:  # pragma: no cover
    from dmr.plugins.msgspec import (
        MsgspecJsonRenderer as JsonRenderer,
    )
except ImportError:  # pragma: no cover
    from dmr.renderers import (  # type: ignore[assignment]
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
            {get_schema_name(type(to_serialize)): to_serialize},
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
        serializer_hook: Callable[[Any], Any],
    ) -> Callable[[str, Any], tuple[str, Any]]:
        def factory(xml_key: str, xml_value: Any) -> tuple[str, Any]:
            try:  # noqa: SIM105
                xml_value = serializer_hook(xml_value)
            except InternalServerError:
                pass  # noqa: WPS420
            return xml_key, xml_value

        return factory


@final
class _RequestModel(pydantic.BaseModel):
    payment_method_id: str
    payment_amount: str


@final
class ContentNegotiationController(
    Controller[PydanticSerializer],
    Body[_RequestModel],
):
    parsers = (JsonParser(), XmlParser())
    renderers = (JsonRenderer(), XmlRenderer())

    def post(
        self,
    ) -> Annotated[
        _RequestModel | list[str],
        conditional_type({
            ContentType.json: list[str],
            ContentType.xml: _RequestModel,
        }),
    ]:
        if self.request.accepts(ContentType.json):
            return [
                self.parsed_body.payment_method_id,
                self.parsed_body.payment_amount,
            ]
        return self.parsed_body

    @validate(
        ResponseSpec(
            return_type=Annotated[
                _RequestModel | list[str],
                conditional_type({
                    ContentType.json: list[str],
                    ContentType.xml: _RequestModel,
                }),
            ],
            status_code=HTTPStatus.CREATED,
        ),
    )
    def put(self) -> HttpResponse:
        if self.request.accepts(ContentType.json):
            return self.to_response(
                [
                    self.parsed_body.payment_method_id,
                    self.parsed_body.payment_amount,
                ],
                status_code=HTTPStatus.CREATED,
            )
        return self.to_response(
            self.parsed_body,
            status_code=HTTPStatus.CREATED,
        )
