import functools
import json
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from types import MappingProxyType
from typing import Any, cast

import pytest
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.test import AsyncRequestFactory, RequestFactory
from django.urls import path
from django.views import View
from syrupy.assertion import SnapshotAssertion

from dmr.adapters import adapt_django_view
from dmr.openapi import build_schema
from dmr.openapi.objects import Operation, PathItem, Response
from dmr.routing import Router

_CSV_PAYLOAD = b'id,name\n'
_AnyView = Callable[..., HttpResponseBase]
_AnyAsyncView = Callable[..., Awaitable[HttpResponseBase]]


class _LegacyExportView(View):
    """Plain Django view that was never rewritten as a controller."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the report the way plain Django would."""
        return HttpResponse(_CSV_PAYLOAD, content_type='text/csv')


class _LegacyAsyncExportView(View):
    """Async flavour of the very same legacy view."""

    async def get(self, request: HttpRequest) -> HttpResponse:
        """Render the report the way plain Django would."""
        return HttpResponse(_CSV_PAYLOAD, content_type='text/csv')


_TYPED_PATH_ITEM = PathItem(
    summary='Legacy CSV export',
    get=Operation(
        summary='Export report as CSV',
        responses={'200': Response(description='CSV payload')},
    ),
)

# The same document, written the way it is spelled in an OpenAPI file.
# `deprecated` is explicit here because a typed `Operation` always emits it.
_RAW_PATH_ITEM = MappingProxyType({
    'summary': 'Legacy CSV export',
    'get': {
        'summary': 'Export report as CSV',
        'responses': {'200': {'description': 'CSV payload'}},
        'deprecated': False,
    },
})

_TypedExport = adapt_django_view(
    _LegacyExportView,
    openapi=_TYPED_PATH_ITEM,
)
_RawExport = adapt_django_view(
    _LegacyExportView,
    openapi=_RAW_PATH_ITEM,
)
_AsyncExport = adapt_django_view(
    _LegacyAsyncExportView,
    openapi=_TYPED_PATH_ITEM,
)


def _build_schema(
    view: _AnyView,
    *,
    skip_validation: bool = False,
) -> dict[str, Any]:
    return build_schema(
        Router('api/', [path('legacy/export/', view)]),
    ).convert(skip_validation=skip_validation)


def _wrap_view(view: _AnyView) -> _AnyView:
    @functools.wraps(view)
    def wrapper(
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        return view(request, *args, **kwargs)

    return wrapper


def test_adapted_view_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that a plain Django view appears in the specification."""
    assert (
        json.dumps(_build_schema(_TypedExport.as_view()), indent=2) == snapshot
    )


def test_raw_mapping_matches_typed_objects() -> None:
    """Ensure that a mapping and typed objects describe the same path."""
    assert _build_schema(_RawExport.as_view()) == _build_schema(
        _TypedExport.as_view(),
    )


def test_path_item_reference() -> None:
    """Ensure that a ``$ref`` path item is passed through untranslated."""
    referenced = adapt_django_view(
        _LegacyExportView,
        openapi={'$ref': '#/components/pathItems/LegacyExport'},
    )

    schema = _build_schema(referenced.as_view(), skip_validation=True)

    assert schema['paths']['/api/legacy/export/'] == {
        '$ref': '#/components/pathItems/LegacyExport',
    }


def test_unknown_path_item_key() -> None:
    """Ensure that an unsupported key is reported, not silently dropped."""
    with pytest.raises(TypeError, match='x-vendor'):
        adapt_django_view(_LegacyExportView, openapi={'x-vendor': 'nope'})


def test_adapted_view_dispatches_as_plain_django(rf: RequestFactory) -> None:
    """Ensure that the adapter does not enrol the view into the pipeline."""
    request = rf.get(
        '/api/legacy/export/',
        headers={'accept': 'application/xml'},
    )

    response = _TypedExport.as_view()(request)

    # A `dmr` controller would fail the content negotiation with a `406`:
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'text/csv'
    assert response.content == _CSV_PAYLOAD


def test_adapted_view_errors_stay_django_shaped(rf: RequestFactory) -> None:
    """Ensure that errors keep the shape plain Django gives them."""
    response = _TypedExport.as_view()(rf.post('/api/legacy/export/'))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert not response.content


async def test_adapted_async_view(async_rf: AsyncRequestFactory) -> None:
    """Ensure that async views can be adapted as well."""
    view = cast('_AnyAsyncView', _AsyncExport.as_view())

    response = await view(async_rf.get('/api/legacy/export/'))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.content == _CSV_PAYLOAD


def test_decorated_view_is_still_collected(rf: RequestFactory) -> None:
    """Ensure that ``functools.wraps`` chains stay discoverable."""
    decorated = _wrap_view(_TypedExport.as_view())

    schema = _build_schema(decorated)

    assert schema['paths']['/api/legacy/export/']['summary'] == (
        'Legacy CSV export'
    )
    assert decorated(rf.get('/api/legacy/export/')).status_code == HTTPStatus.OK
