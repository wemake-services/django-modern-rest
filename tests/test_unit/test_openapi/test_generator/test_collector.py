from collections.abc import Sequence
from typing import final

import pytest
from django.urls import URLPattern, URLResolver, include, path
from django.views import View

from django_modern_rest import Controller
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.openapi.generator.collector import (
    EndpointInfo,
    _extract_endpoints,
    _join_paths,
    _process_pattern,
    _process_resolver,
    collect_endpoints,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.routing import Router, compose_controllers


@final
class _FullController(Controller[PydanticSerializer]):
    """Test controller with API endpoints."""

    def get(self) -> str:
        """GET endpoint."""
        raise NotImplementedError

    def post(self) -> str:
        """POST endpoint."""
        raise NotImplementedError

    def put(self) -> str:
        """PUT endpoint."""
        raise NotImplementedError

    def patch(self) -> str:
        """PATCH endpoint."""
        raise NotImplementedError

    def delete(self) -> str:
        """DELETE endpoint."""
        raise NotImplementedError


@final
class _GetController(Controller[PydanticSerializer]):
    """Test controller with single API endpoint."""

    def get(self) -> str:
        """GET endpoint."""
        raise NotImplementedError


@final
class _PostController(Controller[PydanticSerializer]):
    """Test controller with single API endpoint."""

    def post(self) -> str:
        """POST endpoint."""
        raise NotImplementedError


@final
class _EmptyController(Controller[PydanticSerializer]):
    """Test controller with no API endpoints."""

    def incorrect_method(self) -> str:
        """Non-API method that should be ignored."""
        raise NotImplementedError


@pytest.mark.parametrize(
    ('base_path', 'pattern_path', 'expected'),
    [
        # Empty cases
        ('', '', ''),
        ('', 'api', 'api'),
        ('api', '', 'api'),
        # Basic combinations
        ('api', 'users', 'api/users'),
        ('api/', 'users', 'api/users'),
        ('api', 'users/', 'api/users/'),
        ('api/', 'users/', 'api/users/'),
        # Complex paths
        ('api/v1', 'users/{id}', 'api/v1/users/{id}'),
        ('api/v1/', 'users/{id}/', 'api/v1/users/{id}/'),
        ('/api/v1', '/users/{id}/', '/api/v1/users/{id}/'),
        ('/api/v1/', '/users/{id}/', '/api/v1/users/{id}/'),
        # Edge cases
        ('api/', '', 'api/'),
        ('api/', '/', 'api/'),
        ('', 'users/', 'users/'),
        ('api', '/users/', 'api/users/'),
        ('/api', 'users/', '/api/users/'),
    ],
)
def test_join_paths(
    base_path: str,
    pattern_path: str,
    expected: str,
) -> None:
    """Ensure that `_join_paths` correctly combines base and pattern paths."""
    assert _join_paths(base_path, pattern_path) == expected


@pytest.mark.parametrize(
    ('controller_class', 'expected_count'),
    [
        (_FullController, 5),
        (_GetController, 1),
        (_EmptyController, 0),
    ],
)
def test_extract_endpoints(
    controller_class: type[Controller[PydanticSerializer]],
    expected_count: int,
) -> None:
    """Ensure that `_extract_endpoints` extracts correct number of endpoints."""
    path = '/api/test/'
    endpoints = _extract_endpoints(path, controller_class())

    assert len(endpoints) == expected_count
    assert all(isinstance(endpoint, EndpointInfo) for endpoint in endpoints)
    assert all(endpoint.path == path for endpoint in endpoints)
    assert all(
        isinstance(endpoint.endpoint, Endpoint) for endpoint in endpoints
    )


@pytest.mark.parametrize(
    ('path_str', 'view_class', 'expected_count'),
    [
        ('full/', _FullController, 5),
        ('composed', compose_controllers(_GetController, _PostController), 2),
        ('sla/shed/', _GetController, 1),
        ('', _EmptyController, 0),
    ],
)
def test_process_pattern_with_different_views(
    path_str: str,
    view_class: type[View],
    expected_count: int,
) -> None:
    """Ensure that `_process_pattern` processes different types correctly."""
    pattern = path(path_str, view_class.as_view())
    endpoints = _process_pattern(pattern, '/api/')

    assert len(endpoints) == expected_count
    assert all(isinstance(endpoint, EndpointInfo) for endpoint in endpoints)
    assert all(endpoint.path == f'/api/{path_str}' for endpoint in endpoints)


@pytest.mark.parametrize(
    ('nested_patterns', 'expected_count'),
    [
        ([path('nested/', _GetController.as_view())], 1),
        ([path('nested/', _FullController.as_view())], 5),
        (
            [
                path(
                    'nested/',
                    compose_controllers(
                        _GetController,
                        _PostController,
                    ).as_view(),
                ),
            ],
            2,
        ),
        (
            [
                path(
                    'nested/',
                    include([path('inner/', _FullController.as_view())])
                ),
            ],
            5,
        )
    ],
)
def test_process_resolver_with_nested_patterns(
    nested_patterns: list[URLPattern],
    expected_count: int,
) -> None:
    """Test _process_resolver with nested URL resolvers."""
    resolver = path('api/', include(nested_patterns))
    endpoints = _process_resolver(resolver, '/base/')

    assert len(endpoints) == expected_count
    assert all(isinstance(endpoint, EndpointInfo) for endpoint in endpoints)


def test_collect_endpoints_with_router() -> None:
    """Test the main collect_endpoints function with a Router."""
    patterns: Sequence[URLPattern | URLResolver] = [
        path('direct/', _GetController.as_view()),
        path('nested/', include([path('inner/', _PostController.as_view())])),
        path(
            'composed/',
            compose_controllers(_GetController, _PostController).as_view(),
        ),
    ]
    endpoints = collect_endpoints(Router(patterns))

    assert len(endpoints) == 4
    assert all(isinstance(endpoint, EndpointInfo) for endpoint in endpoints)
