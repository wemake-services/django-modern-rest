import re
from typing import Any

import pydantic
import pytest
from django.urls import URLPattern, URLResolver, include, path, re_path
from inline_snapshot import snapshot

from dmr import Controller, Path
from dmr.exceptions import EndpointMetadataError
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _UserPath(pydantic.BaseModel):
    id: int


class _ExtraFieldPath(pydantic.BaseModel):
    id: int
    extra: int


class _OrgUserPath(pydantic.BaseModel):
    org: int
    id: int


class _UserController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_UserPath]) -> None:
        raise NotImplementedError


class _ExtraFieldController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_ExtraFieldPath]) -> None:
        raise NotImplementedError


class _OrgUserController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_OrgUserPath]) -> None:
        raise NotImplementedError


def _path_params(url: URLPattern | URLResolver, openapi_path: str) -> Any:
    schema = build_schema(Router('api/', [url])).convert()
    return schema['paths'][openapi_path]['get'].get('parameters')


@pytest.mark.parametrize(
    'url',
    [
        path('users/<int:id>/', _ExtraFieldController.as_view()),
        re_path(r'^users/(?P<id>[0-9]+)/$', _ExtraFieldController.as_view()),
        path('users/<int:id>/', _ExtraFieldController.as_view(), {'id': 1}),
    ],
)
def test_path_field_not_in_url(url: URLPattern) -> None:
    """Ensure that `Path` fields must be in the url or in its kwargs."""
    with pytest.raises(
        EndpointMetadataError,
        match=re.escape(
            f"Path parameters ['extra'] of {_ExtraFieldController!r} "
            f"are not found in 'api/{url.pattern}' url and its kwargs",
        ),
    ):
        build_schema(Router('api/', [url]))


def test_url_param_not_in_model() -> None:
    """Ensure that url params missing from `Path` use their converters."""
    assert _path_params(
        path('users/<int:id>/<slug:slug>/', _UserController.as_view()),
        '/api/users/{id}/{slug}/',
    ) == snapshot([
        {
            'name': 'id',
            'in': 'path',
            'schema': {'type': 'integer', 'title': 'Id'},
            'required': True,
        },
        {
            'name': 'slug',
            'in': 'path',
            'schema': {
                'type': 'string',
                'pattern': '^(?:[-a-zA-Z0-9_]+)$',
                'title': 'Slug',
            },
            'required': True,
        },
    ])


def test_re_path_group_not_in_model() -> None:
    """Ensure that `re_path` groups missing from `Path` are documented."""
    assert _path_params(
        re_path(
            r'^users/(?P<id>[0-9]+)/(?P<slug>[a-z]+)/$',
            _UserController.as_view(),
        ),
        '/api/users/{id}/{slug}/',
    ) == snapshot([
        {
            'name': 'id',
            'in': 'path',
            'schema': {'type': 'integer', 'title': 'Id'},
            'required': True,
        },
        {
            'name': 'slug',
            'in': 'path',
            'schema': {
                'type': 'string',
                'pattern': '^(?:[a-z]+)$',
                'title': 'Slug',
            },
            'required': True,
        },
    ])


@pytest.mark.parametrize(
    'url',
    [
        path('users/', _UserController.as_view(), {'id': 1}),
        path(
            'users/',
            include([path('', _UserController.as_view())]),
            {'id': 1},
        ),
    ],
)
def test_path_field_from_kwargs(url: URLPattern | URLResolver) -> None:
    """Ensure that `Path` fields from url kwargs are not in the schema."""
    assert _path_params(url, '/api/users/') is None


def test_path_field_in_url_and_kwargs() -> None:
    """Ensure that `Path` fields in the url are documented even with kwargs."""
    assert _path_params(
        path('users/<int:id>/', _UserController.as_view(), {'id': 1}),
        '/api/users/{id}/',
    ) == snapshot([
        {
            'name': 'id',
            'in': 'path',
            'schema': {'type': 'integer', 'title': 'Id'},
            'required': True,
        },
    ])


def test_path_fields_from_include_prefix() -> None:
    """Ensure that url params from `include()` prefixes are found."""
    assert _path_params(
        path(
            'orgs/<int:org>/',
            include([
                re_path(
                    r'^users/(?P<id>[0-9]+)/$',
                    _OrgUserController.as_view(),
                ),
            ]),
        ),
        '/api/orgs/{org}/users/{id}/',
    ) == snapshot([
        {
            'name': 'org',
            'in': 'path',
            'schema': {'type': 'integer', 'title': 'Org'},
            'required': True,
        },
        {
            'name': 'id',
            'in': 'path',
            'schema': {'type': 'integer', 'title': 'Id'},
            'required': True,
        },
    ])
