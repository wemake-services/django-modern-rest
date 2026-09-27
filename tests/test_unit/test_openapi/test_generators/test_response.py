from http import HTTPMethod, HTTPStatus
from typing import Final

import pytest
from django.conf import LazySettings
from inline_snapshot import snapshot

from dmr.controller import Controller
from dmr.cookies import CookieSpec, NewCookie
from dmr.endpoint import modify
from dmr.headers import HeaderSpec, NewHeader
from dmr.openapi import build_schema
from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.response import ResponseGenerator
from dmr.openapi.objects import (
    Header,
    MediaType,
    OpenAPIType,
    Reference,
    Response,
    Schema,
)
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import FileRenderer, JsonRenderer
from dmr.routing import Router, path
from dmr.settings import Settings

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
    response = generator(
        _ControllerWithCookies.api_endpoints[HTTPMethod.POST].metadata,
        _ControllerWithCookies,
    )
    response_created = response['201']

    assert isinstance(response_created, Response)
    assert response_created.headers is not None
    assert response_created.headers == snapshot({
        'Set-Cookie: first_cookie': Header(
            schema=Schema(type=OpenAPIType.STRING),
            description='First',
            required=True,
        ),
        'Set-Cookie: second_cookie': Header(
            schema=Schema(type=OpenAPIType.STRING),
            description='Second',
        ),
        'Set-Cookie: third_cookie': Header(
            schema=Schema(type=OpenAPIType.STRING),
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
    response = generator(
        _ControllerWithHeaders.api_endpoints[HTTPMethod.GET].metadata,
        _ControllerWithHeaders,
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
    controller = _ControllerWithMultipleRenderers
    response = generator(
        controller.api_endpoints[HTTPMethod.POST].metadata,
        controller,
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


def _single_example(header: Header | Reference) -> str:
    """Return the only generated example of a header."""
    assert isinstance(header, Header)
    assert isinstance(header.schema, Schema)
    assert header.schema.examples is not None
    return str(header.schema.examples[0])


def _cookie_examples(response: Response) -> dict[str, str]:
    """Collect the generated example of every cookie header."""
    assert response.headers is not None
    return {
        header_name: _single_example(header)
        for header_name, header in response.headers.items()
    }


def test_response_generator_cookie_examples(settings: LazySettings) -> None:
    """Ensure that cookie examples come from the example generation."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}
    # A context seeds the examples when it is created, so it cannot come
    # from a fixture here: the seed must be set before that happens.
    context = OpenAPIContext(OpenAPIConfig(title='tests', version='0.0.1'))

    response = context.generators.response(
        _ControllerWithCookies.api_endpoints[HTTPMethod.POST].metadata,
        _ControllerWithCookies,
    )['201']

    assert isinstance(response, Response)
    examples = _cookie_examples(response)

    assert list(examples) == snapshot([
        'Set-Cookie: first_cookie',
        'Set-Cookie: second_cookie',
        'Set-Cookie: third_cookie',
    ])
    # Every cookie takes its own value from the generator, they used to
    # share a static `123`. We don't assert the values themselves: they
    # are random strings, and pinning them here upsets the spell checker.
    assert len(set(examples.values())) == len(examples)
    assert all(
        example.split('=', 1)[0] == header_name.removeprefix('Set-Cookie: ')
        for header_name, example in examples.items()
    )


class _ControllerWithHeaderExamples(Controller[PydanticSerializer]):
    @modify(
        headers={
            'X-Request-Id': NewHeader(value='abc', example='abc'),
            'X-Token': HeaderSpec(example='secret', skip_validation=True),
            'X-Other-Test-Header': _HEADER,
        },
    )
    def get(self) -> str:
        raise NotImplementedError


def test_header_examples_replace_generated(
    *,
    settings: LazySettings,
) -> None:
    """Ensure that header examples replace the generated ones."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1627
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}
    # A context seeds the examples when it is created, so it cannot come
    # from a fixture here: the seed must be set before that happens.
    context = OpenAPIContext(OpenAPIConfig(title='tests', version='0.0.1'))

    response = context.generators.response(
        _ControllerWithHeaderExamples.api_endpoints[HTTPMethod.GET].metadata,
        _ControllerWithHeaderExamples,
    )['200']

    assert isinstance(response, Response)
    assert response.headers is not None
    assert len(response.headers) == 3
    assert response.headers['X-Request-Id'] == snapshot(
        Header(
            schema=Schema(type=OpenAPIType.STRING),
            required=True,
            example='abc',
        ),
    )
    assert response.headers['X-Token'] == snapshot(
        Header(
            schema=Schema(type=OpenAPIType.STRING),
            required=True,
            example='secret',
        ),
    )
    # Headers without an example still get a generated one:
    assert _single_example(response.headers['X-Other-Test-Header'])


@pytest.mark.parametrize('openapi_version', ['3.1.0', '3.2.0'])
def test_header_examples_schema(*, openapi_version: str) -> None:
    """Ensure that header examples pass the OpenAPI validation."""
    schema = build_schema(
        Router(
            'api/',
            [path('user/', _ControllerWithHeaderExamples.as_view())],
        ),
        config=OpenAPIConfig(
            title='tests',
            version='0.0.1',
            openapi_version=openapi_version,
        ),
    ).convert()

    operation = schema['paths']['/api/user/']['get']
    assert operation['responses']['200']['headers'] == snapshot({
        'X-Other-Test-Header': {
            'schema': {'type': 'string'},
            'description': 'Other Test Header',
            'required': True,
        },
        'X-Request-Id': {
            'schema': {'type': 'string'},
            'required': True,
            'example': 'abc',
        },
        'X-Token': {
            'schema': {'type': 'string'},
            'required': True,
            'example': 'secret',
        },
    })
