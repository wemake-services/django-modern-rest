from collections.abc import Sequence
from typing import Any, final

import pytest
from django.urls import URLPattern, URLResolver, include, path

from django_modern_rest import Controller
from django_modern_rest.openapi.collector import (
    ControllerMapping,
    _join_paths,
    _process_pattern,
    _process_resolver,
    controller_collector,
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
    ('path_str', 'view_class'),
    [
        ('full/', _FullController),
        ('composed', compose_controllers(_GetController, _PostController)),
        ('sla/shed/', _GetController),
        ('', _EmptyController),
    ],
)
def test_process_pattern_with_different_views(
    path_str: str,
    view_class: type[Controller[Any]],
) -> None:
    """Ensure that `_process_pattern` processes different types correctly."""
    pattern = path(path_str, view_class.as_view())
    controller_mapping = _process_pattern(pattern, '/api/')

    assert isinstance(controller_mapping, ControllerMapping)
    assert controller_mapping.path == f'/api/{path_str}'


@pytest.mark.parametrize(
    'view_func',
    [
        _EmptyController.as_view(),
        _FullController.as_view(),
        compose_controllers(_GetController, _PostController).as_view(),
        include([path('inner/', _FullController.as_view())]),
    ],
)
def test_process_resolver_with_nested_patterns(view_func: Any) -> None:
    """Test _process_resolver with nested URL resolvers."""
    nested_patterns = [path('nested/', view_func)]
    resolver = path('api/', include((nested_patterns, 'test_app')))
    controllers = _process_resolver(resolver, '/base/')

    assert all(
        isinstance(controller, ControllerMapping) for controller in controllers
    )


def test_controller_collector_with_router() -> None:
    """Test the main controller_collector function with a Router."""
    patterns: Sequence[URLPattern | URLResolver] = [
        path('direct/', _GetController.as_view()),
        path('nested/', include([path('inner/', _PostController.as_view())])),
        path(
            'composed/',
            compose_controllers(_GetController, _PostController).as_view(),
        ),
    ]
    controllers = controller_collector(Router(patterns))

    assert len(controllers) == 3
    assert all(
        isinstance(controller, ControllerMapping) for controller in controllers
    )
