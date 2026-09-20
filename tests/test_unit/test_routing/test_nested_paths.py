from collections.abc import Callable, Sequence
from typing import Any

import pytest
from django.urls import URLPattern, URLResolver, include, re_path
from django.urls import path as django_path
from inline_snapshot import snapshot

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path


class _GetController(Controller[PydanticSerializer]):
    """Test controller with single API endpoint."""

    def get(self) -> str:
        raise NotImplementedError


def test_nested_url_patterns() -> None:
    """Ensure that nested URL patterns produce all path parameters."""
    patterns: Sequence[URLPattern | URLResolver] = [
        path(
            'tn/<int:tenant>/',
            include([
                path('us/<path:pk>/', _GetController.as_view()),
            ]),
        ),
    ]
    router = Router('api/<slug:version>/', patterns)

    schema = build_schema(router).convert()

    assert schema['paths']['/api/{version}/tn/{tenant}/us/{pk}/']['get'][
        'parameters'
    ] == snapshot([
        {
            'name': 'version',
            'in': 'path',
            'schema': {
                'type': 'string',
                'pattern': '^(?:[-a-zA-Z0-9_]+)$',
                'title': 'Version',
            },
            'required': True,
        },
        {
            'name': 'tenant',
            'in': 'path',
            'schema': {'type': 'integer', 'title': 'Tenant'},
            'required': True,
        },
        {
            'name': 'pk',
            'in': 'path',
            'schema': {
                'type': 'string',
                'title': 'Pk',
                'description': 'Can contain slashes',
            },
            'required': True,
        },
    ])


@pytest.mark.parametrize('path_func', [path, django_path])
def test_deeply_nested_url_patterns(
    *,
    path_func: Callable[..., Any],
) -> None:
    """Ensure that nested URL patterns produce all path parameters."""
    patterns: Sequence[URLPattern | URLResolver] = [
        path_func(
            '<int:tenant>/',
            include([
                path_func(
                    '<path:pk>/',
                    include([
                        path_func('<str:fin>/', _GetController.as_view()),
                    ]),
                ),
            ]),
        ),
    ]
    router = Router('api/<slug:version>/', patterns)

    schema = build_schema(router).convert()

    assert schema['paths']['/api/{version}/{tenant}/{pk}/{fin}/']['get'][
        'parameters'
    ] == snapshot([
        {
            'name': 'version',
            'in': 'path',
            'schema': {
                'type': 'string',
                'pattern': '^(?:[-a-zA-Z0-9_]+)$',
                'title': 'Version',
            },
            'required': True,
        },
        {
            'name': 'tenant',
            'in': 'path',
            'schema': {'type': 'integer', 'title': 'Tenant'},
            'required': True,
        },
        {
            'name': 'pk',
            'in': 'path',
            'schema': {
                'type': 'string',
                'title': 'Pk',
                'description': 'Can contain slashes',
            },
            'required': True,
        },
        {
            'name': 'fin',
            'in': 'path',
            'schema': {'type': 'string', 'title': 'Fin'},
            'required': True,
        },
    ])


def test_deeply_nested_url_re_patterns() -> None:
    """Ensure that nested URL patterns produce all re_path parameters."""
    patterns: Sequence[URLPattern | URLResolver] = [
        re_path(
            r'(?P<year>[0-9]{4})/',
            include([
                re_path(
                    r'(?P<month>\d+)/',
                    include([
                        re_path(r'(?P<day>\w+)/', _GetController.as_view()),
                    ]),
                ),
            ]),
        ),
    ]
    router = Router(r'api/(?P<slug>[\w-]+)/', patterns)

    schema = build_schema(router).convert()

    assert schema['paths']['/api/{slug}/{year}/{month}/{day}/']['get'][
        'parameters'
    ] == snapshot([
        {
            'name': 'slug',
            'in': 'path',
            'schema': {
                'type': 'string',
                'pattern': r'^(?:[\w-]+)$',
                'title': 'Slug',
            },
            'required': True,
        },
        {
            'name': 'year',
            'in': 'path',
            'schema': {
                'type': 'string',
                'pattern': '^(?:[0-9]{4})$',
                'title': 'Year',
            },
            'required': True,
        },
        {
            'name': 'month',
            'in': 'path',
            'schema': {
                'type': 'string',
                'pattern': r'^(?:\d+)$',
                'title': 'Month',
            },
            'required': True,
        },
        {
            'name': 'day',
            'in': 'path',
            'schema': {
                'type': 'string',
                'pattern': r'^(?:\w+)$',
                'title': 'Day',
            },
            'required': True,
        },
    ])
