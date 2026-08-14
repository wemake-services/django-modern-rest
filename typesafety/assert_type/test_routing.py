from typing import assert_type

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    JsonResponse,
)
from django.urls import URLPattern
from django.views import View

from dmr.routing import path


def sync_func(request: HttpRequest) -> HttpResponseBase:
    raise NotImplementedError


assert_type(path('/', sync_func), URLPattern)
assert_type(path('/', sync_func, name='test'), URLPattern)
assert_type(path('/', sync_func, {}), URLPattern)
assert_type(path('/', sync_func, {}, name='test'), URLPattern)


async def async_func(request: HttpRequest) -> JsonResponse:
    raise NotImplementedError


assert_type(path('/', async_func), URLPattern)
assert_type(path('/', async_func, {}), URLPattern)
assert_type(path('/', async_func, {}), URLPattern)
assert_type(path('/', async_func, {}, name='test'), URLPattern)


class ClassView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        raise NotImplementedError


assert_type(path('/', ClassView.as_view()), URLPattern)
assert_type(path('/', ClassView.as_view(), {}), URLPattern)
assert_type(path('/', ClassView.as_view(), {}), URLPattern)
assert_type(path('/', ClassView.as_view(), {}, name='test'), URLPattern)
path('/', ClassView), URLPattern  # type: ignore[arg-type]  # ty: ignore[no-matching-overload]
