import datetime as dt
import uuid
from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any, ClassVar, TypeAlias, final

import pydantic
import xmltodict
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from typing_extensions import override

from django_modern_rest import (  # noqa: WPS235
    Blueprint,
    Body,
    Controller,
    Headers,
    Path,
    Query,
    ResponseSpec,
    modify,
    validate,
)
from django_modern_rest.exceptions import (
    ResponseSerializationError,
)
from django_modern_rest.negotiation import ContentType, conditional_type
from django_modern_rest.parsers import DeserializeFunc, Parser, Raw
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.renderers import Renderer
from server.apps.controllers.auth import HttpBasicAsync, HttpBasicSync

_CallableAny: TypeAlias = Callable[..., Any]


@final
class _QueryData(pydantic.BaseModel):
    query: str = pydantic.Field(alias='q')
    start_from: dt.datetime | None = None


@final
class _CustomHeaders(pydantic.BaseModel):
    token: str = pydantic.Field(alias='X-API-Token')


class _UserInput(pydantic.BaseModel):
    email: str
    age: int


@final
class _UserOutput(_UserInput):
    uid: uuid.UUID
    token: str
    query: str
    start_from: dt.datetime | None


@final
class _UserPath(pydantic.BaseModel):
    user_id: int


@final
class _ConstrainedUserSchema(pydantic.BaseModel):
    username: str = pydantic.Field(
        min_length=3,
        max_length=20,  # noqa: WPS432
        pattern=r'^[a-z0-9_]+$',
    )
    age: int = pydantic.Field(ge=18, le=100)  # noqa: WPS432
    score: float = pydantic.Field(gt=0, lt=1.5)  # noqa: WPS432


@final
class UserCreateBlueprint(  # noqa: WPS215
    Query[_QueryData],
    Headers[_CustomHeaders],
    Body[_UserInput],
    Blueprint[PydanticSerializer],
):
    def post(self) -> _UserOutput:
        return _UserOutput(
            uid=uuid.uuid4(),
            email=self.parsed_body.email,
            age=self.parsed_body.age,
            token=self.parsed_headers.token,
            query=self.parsed_query.query,
            start_from=self.parsed_query.start_from,
        )


@final
class UserListBlueprint(Blueprint[PydanticSerializer]):
    def get(self) -> list[_UserInput]:
        return [
            _UserInput(email='first@example.org', age=1),
            _UserInput(email='second@example.org', age=2),
        ]


@final
class UserUpdateBlueprint(
    Body[_UserInput],
    Blueprint[PydanticSerializer],
    Path[_UserPath],
):
    async def patch(self) -> _UserInput:
        return _UserInput(
            email=self.parsed_body.email,
            age=self.parsed_path.user_id,
        )


@final
class UserReplaceBlueprint(
    Blueprint[PydanticSerializer],
    Path[_UserPath],
):
    @validate(
        ResponseSpec(
            return_type=_UserInput,
            status_code=HTTPStatus.OK,
        ),
    )
    async def put(self) -> HttpResponse:
        return self.to_response({
            'email': 'new@email.com',
            'age': self.parsed_path.user_id,
        })


@final
class ParseHeadersController(
    Headers[_CustomHeaders],
    Controller[PydanticSerializer],
):
    auth = (HttpBasicSync(),)

    def post(self) -> _CustomHeaders:
        return self.parsed_headers


@final
class AsyncParseHeadersController(
    Headers[_CustomHeaders],
    Controller[PydanticSerializer],
):
    @modify(auth=[HttpBasicAsync()])
    async def post(self) -> _CustomHeaders:
        return self.parsed_headers


# NOTE: this is a overly-simplified example of xml parsing / rendering.
# You *will* need more work.
@final
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


@final
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
        assert isinstance(raw_data, str)  # noqa: S101
        return raw_data.encode('utf8')

    @classmethod
    def _wrap_serializer(
        cls,
        serializer: Callable[[Any], Any],
    ) -> Callable[[str, Any], tuple[str, Any]]:
        def factory(xml_key: str, xml_value: Any) -> tuple[str, Any]:
            try:  # noqa: SIM105
                xml_value = serializer(xml_value)
            except ResponseSerializationError:
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
    parsers = (XmlParser,)
    renderers = (XmlRenderer,)

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


@final
class ConstrainedUserController(
    Body[_ConstrainedUserSchema],
    Controller[PydanticSerializer],
):
    def post(self) -> _ConstrainedUserSchema:
        return self.parsed_body
