from http import HTTPMethod, HTTPStatus
from typing import Final

import pytest
from inline_snapshot import snapshot

from dmr.controller import Controller
from dmr.cookies import CookieSpec, NewCookie
from dmr.endpoint import modify
from dmr.headers import HeaderSpec, NewHeader
from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.response import ResponseGenerator
from dmr.openapi.mappers import TypeMapper
from dmr.openapi.objects import (
    Header,
    Reference,
    Response,
    Schema,
)
from dmr.openapi.objects.enums import OpenAPIType
from dmr.openapi.objects.media_type import MediaType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import FileRenderer, JsonRenderer

_TEST_CONFIG: Final = OpenAPIConfig(title='Test API', version='1.0.0')
_SCHEMA_ONLY_HEADER: Final = HeaderSpec(
    description='Test Header',
    required=True,
    schema_only=True,
)
_HEADER: Final = NewHeader(
    value='Test',
    description='Other Test Header',
)


class _ControllerWithCookies(Controller[PydanticSerializer]):
    @modify(
        status_code=HTTPStatus.CREATED,
        cookies={
            'first_cookie': CookieSpec(description='First', schema_only=True),
            'second_cookie': CookieSpec(description='Second', schema_only=True),
            'third_cookie': NewCookie(value='Third'),
        },
    )
    def post(self) -> list[int]:
        raise NotImplementedError


class _ControllerWithHeaders(Controller[PydanticSerializer]):
    @modify(
        headers={
            'X-Test-Header': _SCHEMA_ONLY_HEADER,
            'X-Other-Test-Header': _HEADER,
        },
    )
    def get(self) -> str:
        raise NotImplementedError


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


@pytest.fixture
def context() -> OpenAPIContext:
    """Create ``OpenAPIContext`` instance for testing."""
    return OpenAPIContext(config=_TEST_CONFIG)


@pytest.fixture
def generator(context: OpenAPIContext) -> ResponseGenerator:
    """Create ``ResponseGenerator`` instance for testing."""
    return context.generators.response


def test_response_generator_multiple_cookies(
    generator: ResponseGenerator,
) -> None:
    """Ensure that multiple cookies are handled."""
    controller = _ControllerWithCookies()

    response = generator(controller.api_endpoints[HTTPMethod.POST].metadata)
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
            required=True,
        ),
        'Set-Cookie: third_cookie': Header(
            schema=Schema(type=OpenAPIType.STRING, example='third_cookie=123'),
            required=True,
        ),
    })


def test_response_generator_headers(
    generator: ResponseGenerator,
) -> None:
    """Ensure that headers are handled."""
    controller = _ControllerWithHeaders()

    response = generator(controller.api_endpoints[HTTPMethod.GET].metadata)
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


def test_response_generator_cookie_with_reference(
    context: OpenAPIContext,
) -> None:
    """Ensure that cookies with reference schemas are handled."""
    # We manually remove str from TypeMapper to force SchemaGenerator
    # to look into the registry.
    TypeMapper._mapping.pop(str)
    string_ref = 'StringRef'
    context.registries.schema.register(
        source_type=str,
        schema=Schema(type=OpenAPIType.STRING),
        name=string_ref,
    )
    controller = _ControllerWithCookies()

    response = context.generators.response(
        controller.api_endpoints[HTTPMethod.POST].metadata,
    )

    response_created = response['201']
    assert isinstance(response_created, Response)
    assert response_created.headers is not None
    assert response_created.headers == snapshot({
        'Set-Cookie: first_cookie': Header(
            schema=Reference(ref=f'#/components/schemas/{string_ref}'),
            description='First',
            required=True,
        ),
        'Set-Cookie: second_cookie': Header(
            schema=Reference(ref=f'#/components/schemas/{string_ref}'),
            description='Second',
            required=True,
        ),
        'Set-Cookie: third_cookie': Header(
            schema=Reference(ref='#/components/schemas/StringRef'),
            required=True,
        ),
    })


def test_response_multiple_content_types(
    generator: ResponseGenerator,
) -> None:
    """Ensure that multiple content types (from renderers) are handled."""
    controller = _ControllerWithMultipleRenderers()
    response = generator(controller.api_endpoints[HTTPMethod.POST].metadata)

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
