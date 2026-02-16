from http import HTTPMethod, HTTPStatus
from typing import Final

import pytest
from inline_snapshot import snapshot

from django_modern_rest.controller import Controller
from django_modern_rest.cookies import CookieSpec
from django_modern_rest.endpoint import modify
from django_modern_rest.headers import HeaderSpec, NewHeader
from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.openapi.core.context import OpenAPIContext
from django_modern_rest.openapi.generators.response import ResponseGenerator
from django_modern_rest.openapi.objects import (
    Header,
    Reference,
    Response,
    Schema,
)
from django_modern_rest.openapi.objects.enums import OpenAPIType
from django_modern_rest.openapi.type_mapping import TypeMapper
from django_modern_rest.plugins.pydantic import PydanticSerializer

_TEST_CONFIG: Final = OpenAPIConfig(title='Test API', version='1.0.0')


class _ControllerWithCookies(Controller[PydanticSerializer]):
    @modify(
        status_code=HTTPStatus.CREATED,
        cookies={
            'first_cookie': CookieSpec(description='First', schema_only=True),
            'second_cookie': CookieSpec(description='Second', schema_only=True),
        },
    )
    def post(self) -> list[int]:
        raise NotImplementedError


class _ControllerWithHeaders(Controller[PydanticSerializer]):
    @modify(
        headers={
            'X-Test-Header': HeaderSpec(
                description='Test Header',
                required=True,
                schema_only=True,
            ),
            'X-Other-Test-Header': NewHeader(
                value='Test',
                description='Other Test Header',
            ),
        },
    )
    def get(self) -> str:
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
    TypeMapper._type_map.pop(str)
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
    })
