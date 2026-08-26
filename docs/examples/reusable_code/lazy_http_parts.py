from collections.abc import Mapping
from http import HTTPStatus
from typing import ClassVar, TypeVar

from django.http import HttpResponse

from dmr import Controller, CookieSpec, FromController, ResponseSpec, validate
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)


class ReusableCookieController(Controller[_SerializerT]):
    #: Subclasses can rename the cookie without redefining `post`.
    session_cookie: ClassVar[str] = 'session_id'

    @classmethod
    def cookie_specs(cls) -> Mapping[str, CookieSpec]:
        """Single source of truth for the schema and the real cookies."""
        return {cls.session_cookie: CookieSpec(httponly=True, secure=True)}

    @validate(
        ResponseSpec(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            # Resolved against each concrete subclass, not against this class:
            cookies=FromController(cookie_specs),
        ),
    )
    def post(self) -> HttpResponse:
        return self.to_response(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            cookies={
                cookie_key: spec.to_new(self.make_session_id())
                for cookie_key, spec in type(self).cookie_specs().items()
            },
        )

    def make_session_id(self) -> str:
        return 'some-session-id'


class CustomCookieController(ReusableCookieController[PydanticSerializer]):
    #: This name ends up both in the response and in the OpenAPI schema.
    session_cookie: ClassVar[str] = 'custom_session_id'


# run: {"controller": "CustomCookieController", "method": "post", "url": "/api/example/"}  # noqa: ERA001, E501
# openapi: {"controller": "CustomCookieController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
