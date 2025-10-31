from collections.abc import Sequence
from typing import Any, final

import pytest
from django.urls import URLPattern, URLResolver, include, path

from django_modern_rest import Blueprint, Controller
from django_modern_rest.openapi.collector import (
    ControllerMapping,
    _join_paths,
    _normalize_path,
    _process_pattern,
    _process_resolver,
    controller_collector,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.routing import Router, compose_blueprints


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
class _GetBlueprint(Blueprint[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


@final
class _PostBlueprint(Blueprint[PydanticSerializer]):
    def post(self) -> str:
        raise NotImplementedError


@final
class _EmptyController(Controller[PydanticSerializer]):
    """Test controller with no API endpoints."""

    def incorrect_method(self) -> str:
        """Non-API method that should be ignored."""
        raise NotImplementedError


@pytest.mark.parametrize(
    ('input_path', 'expected_output'),
    [
        # Typed parameters
        ('users/<int:user_id>', '/users/{user_id}'),
        ('api/<slug:username>/profile', '/api/{username}/profile'),
        ('api/<str:user>/tags/<int:id>', '/api/{user}/tags/{id}'),
        ('users/<uuid:user_uuid>', '/users/{user_uuid}'),
        # Untyped parameters
        ('files/<filename>', '/files/{filename}'),
        ('tags/<slug>/posts', '/tags/{slug}/posts'),
        # Trailing slashes
        ('users/<int:user_id>/', '/users/{user_id}/'),
        ('api/v1/posts/<int:post_id>/', '/api/v1/posts/{post_id}/'),
        # Multiple params
        ('api/v1/<int:user_id>/posts/<int:id>', '/api/v1/{user_id}/posts/{id}'),
        (
            'shops/<slug:shop_name>/products/<str:product_category>/items/<int:item_id>',
            '/shops/{shop_name}/products/{product_category}/items/{item_id}',
        ),
        # Without parameters (should remain unchanged)
        ('users', '/users'),
        ('api/v1/health', '/api/v1/health'),
        ('api/v1/health/', '/api/v1/health/'),
        # Empty path
        ('', '/'),
        # Paths with regex patterns that simplify_regex processes
        ('^posts/(?P<post_id>\\d+)$', '/posts/{post_id}'),  # noqa: WPS342
        (
            '^api/v1/users/(?P<user_id>\\d+)/posts/(?P<post_id>\\d+)$',  # noqa: WPS342
            '/api/v1/users/{user_id}/posts/{post_id}',
        ),
        # Edge cases
        ('blog/posts/<slug>', '/blog/posts/{slug}'),
        ('/api/users/<int:id>', '/api/users/{id}'),
        ('api/<str:name>/suffix/<int:value>', '/api/{name}/suffix/{value}'),
    ],
)
def test_normalize_path(
    input_path: str,
    expected_output: str,
) -> None:
    """Ensure that `_normalize_path` correctly normalizes patterns."""
    normalized = _normalize_path(input_path)
    assert normalized == expected_output, (
        f'Path normalization failed: '
        f'Input: {input_path!r}; '
        f'Output: {normalized!r}; '
        f'Expected: {expected_output!r}'
    )


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
        ('composed', compose_blueprints(_GetBlueprint, _PostBlueprint)),
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
        compose_blueprints(_GetBlueprint, _PostBlueprint).as_view(),
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
            compose_blueprints(_GetBlueprint, _PostBlueprint).as_view(),
        ),
    ]
    controllers = controller_collector(Router(patterns))

    assert len(controllers) == 3
    assert all(
        isinstance(controller, ControllerMapping) for controller in controllers
    )
