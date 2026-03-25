from http import HTTPMethod, HTTPStatus
from typing import Final

import pytest
from inline_snapshot import snapshot

from dmr.controller import Controller
from dmr.cookies import CookieSpec, NewCookie
from dmr.endpoint import modify
from dmr.headers import HeaderSpec, NewHeader
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.response import ResponseGenerator
from dmr.openapi.objects import Header, MediaType, OpenAPIType, Response, Schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import FileRenderer, JsonRenderer

_SCHEMA_ONLY_HEADER: Final = HeaderSpec(
    description='Test Header',
    required=True,
    skip_validation=True,
)
_HEADER: Final = NewHeader(
    value='Test',
    description='Other Test Header',
)


@pytest.fixture
def generator(openapi_context: OpenAPIContext) -> ResponseGenerator:
    """Create ``ResponseGenerator`` instance for testing."""
    return openapi_context.generators.response


class _ControllerWithCookies(Controller[PydanticSerializer]):
    @modify(
        status_code=HTTPStatus.CREATED,
        cookies={
            'first_cookie': CookieSpec(
                description='First',
                skip_validation=True,
            ),
            'second_cookie': CookieSpec(
                description='Second',
                skip_validation=True,
                required=False,
            ),
            'third_cookie': NewCookie(value='Third'),
        },
    )
    def post(self) -> list[int]:
        raise NotImplementedError


def test_response_generator_multiple_cookies(
    generator: ResponseGenerator,
) -> None:
    """Ensure that multiple cookies are handled."""
    controller = _ControllerWithCookies()

    response = generator(
        controller.api_endpoints[HTTPMethod.POST].metadata,
        PydanticSerializer,
    )
    response_created = response['201']

    assert isinstance(response_created, Response)
    assert response_created.headers is not None
    assert response_created.headers == snapshot({
        'Set-Cookie: first_cookie': Header(
            schema=Schema(type=OpenAPIType.STRING, example='first_cookie=123'),
            description='First',
            required=True,
        ),
        'Set-Cookie: second_cookie': Header(
            schema=Schema(type=OpenAPIType.STRING, example='second_cookie=123'),
            description='Second',
        ),
        'Set-Cookie: third_cookie': Header(
            schema=Schema(type=OpenAPIType.STRING, example='third_cookie=123'),
            required=True,
        ),
    })


class _ControllerWithHeaders(Controller[PydanticSerializer]):
    @modify(
        headers={
            'X-Test-Header': _SCHEMA_ONLY_HEADER,
            'X-Other-Test-Header': _HEADER,
        },
    )
    def get(self) -> str:
        raise NotImplementedError


def test_response_generator_headers(
    generator: ResponseGenerator,
) -> None:
    """Ensure that headers are handled."""
    controller = _ControllerWithHeaders()

    response = generator(
        controller.api_endpoints[HTTPMethod.GET].metadata,
        PydanticSerializer,
    )
    response_ok = response['200']

    assert isinstance(response_ok, Response)
    assert response_ok.headers is not None
    assert response_ok.headers == snapshot({
        'X-Test-Header': Header(
            schema=Schema(type=OpenAPIType.STRING),
            description='Test Header',
            required=True,
        ),
        'X-Other-Test-Header': Header(
            schema=Schema(type=OpenAPIType.STRING),
            description='Other Test Header',
            required=True,
        ),
    })


class _ControllerWithMultipleRenderers(Controller[PydanticSerializer]):
    @modify(
        renderers=[
            JsonRenderer(),
            FileRenderer(content_type='application/pdf'),
        ],
        headers={
            'X-Test-Header': _SCHEMA_ONLY_HEADER,
            'X-Other-Test-Header': _HEADER,
        },
    )
    def post(self) -> str:
        raise NotImplementedError


def test_response_multiple_content_types(
    generator: ResponseGenerator,
) -> None:
    """Ensure that multiple content types (from renderers) are handled."""
    controller = _ControllerWithMultipleRenderers()
    response = generator(
        controller.api_endpoints[HTTPMethod.POST].metadata,
        PydanticSerializer,
    )

    response_created = response['201']

    assert isinstance(response_created, Response)

    assert response_created.headers == snapshot({
        'X-Test-Header': Header(
            schema=Schema(type=OpenAPIType.STRING),
            description='Test Header',
            required=True,
        ),
        'X-Other-Test-Header': Header(
            schema=Schema(type=OpenAPIType.STRING),
            description='Other Test Header',
            required=True,
        ),
    })

    assert response_created.content == snapshot({
        'application/json': MediaType(schema=Schema(type=OpenAPIType.STRING)),
        'application/pdf': MediaType(schema=Schema(type=OpenAPIType.STRING)),
    })
