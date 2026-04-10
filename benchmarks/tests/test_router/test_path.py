from collections.abc import Callable
from contextlib import suppress
from typing import Final, Literal, assert_never

from django.http import HttpRequest, HttpResponse
from django.urls import Resolver404, URLPattern, include
from django.urls import path as django_path
from django.urls.resolvers import RegexPattern, URLResolver
from pytest_codspeed import BenchmarkFixture

from dmr.routing import path as dmr_path


def _a_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse(b'')


def _build_resolver(
    path: Callable[..., URLPattern | URLResolver],
) -> URLResolver:
    inner_patterns = [
        path('users/', _a_view),
        path('users/<int:user_id>', _a_view),
        path('users/<int:user_id>/posts', _a_view),
        path('users/<int:user_id>/posts/<int:post_id>', _a_view),
        path('articles/', _a_view),
        path('articles/<slug:slug>', _a_view),
        path('articles/<slug:slug>/comments', _a_view),
        path('authors/', _a_view),
        path('authors/<int:author_id>', _a_view),
        path('categories/', _a_view),
        path('categories/<slug:category_slug>', _a_view),
        path('tags/', _a_view),
        path('tags/<str:tag_name>', _a_view),
        path('products/', _a_view),
        path('products/<int:product_id>', _a_view),
        path('products/<int:product_id>/reviews', _a_view),
        path('products/<int:product_id>/reviews/<int:review_id>', _a_view),
        path('orders/', _a_view),
        path('orders/<uuid:order_id>', _a_view),
        path('payments/', _a_view),
        path('payments/<uuid:payment_id>', _a_view),
        path('inventory/', _a_view),
        path('inventory/<int:item_id>', _a_view),
        path('suppliers/', _a_view),
        path('suppliers/<int:supplier_id>', _a_view),
        path('customers/', _a_view),
        path('customers/<int:customer_id>', _a_view),
        path('addresses/', _a_view),
        path('addresses/<int:address_id>', _a_view),
        path('notifications/', _a_view),
        path('notifications/<int:notification_id>', _a_view),
        path('settings/', _a_view),
        path('settings/<str:key>', _a_view),
        path('analytics/', _a_view),
        path('analytics/<str:metric>', _a_view),
        path('reports/', _a_view),
        path('reports/<int:report_id>', _a_view),
        path('audit/', _a_view),
        path('audit/<str:audit_id>', _a_view),
        path('health', _a_view),
        path('metrics', _a_view),
    ]
    return URLResolver(
        RegexPattern(r''),
        [
            path(
                'api/',
                include((inner_patterns, 'app-name'), namespace='api'),
            ),
        ],
    )


def _pick_url(case: Literal['best', 'avg', 'worst']) -> str:
    match case:
        case 'best':
            return 'api/users/'
        case 'avg':
            return 'api/tags/sometag'
        case 'worst':
            return 'api/no-such-path/'
        case other:
            assert_never(other)


_REPEAT: Final = 1_000


def test_router_path_native(
    benchmark: BenchmarkFixture,
) -> None:
    """Test Django native version of the ``path`` function."""

    resolver = _build_resolver(django_path)

    @benchmark
    def factory() -> None:
        for _repeat in range(_REPEAT):
            for bench_case in ('best', 'avg', 'worst'):
                with suppress(Resolver404):
                    resolver.resolve(_pick_url(bench_case))


def test_router_path_dmr(
    benchmark: BenchmarkFixture,
) -> None:
    """Test custom DMR version of the ``path`` function."""

    resolver = _build_resolver(dmr_path)

    @benchmark
    def factory() -> None:
        for _repeat in range(_REPEAT):
            for bench_case in ('best', 'avg', 'worst'):
                with suppress(Resolver404):
                    resolver.resolve(_pick_url(bench_case))
