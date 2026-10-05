from collections.abc import Callable, Sequence
from typing import Any

from django.http import HttpResponseBase
from django.views import View
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import Router, path
from dmr.throttling import Rate, SyncThrottle


class ThrottlingMixin(View):
    """Applies ``throttling`` passed to ``as_view``."""

    @override
    @classmethod
    def as_view(
        cls,
        *,
        throttling: Sequence[SyncThrottle] | None = None,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        if throttling is None:
            return super().as_view(**initkwargs)
        # `throttling` is read when a controller class is created,
        # so we apply it to a new subclass:
        throttled_cls: type[ThrottlingMixin] = type(
            cls.__name__,
            (cls,),
            {'throttling': throttling, '__module__': cls.__module__},
        )
        return throttled_cls.as_view(**initkwargs)


class CatalogController(Controller[PydanticFastSerializer], ThrottlingMixin):
    def get(self) -> list[str]:
        return ['book', 'pen']


router = Router(
    'api/',
    [
        path(
            'catalog/',
            CatalogController.as_view(
                throttling=[SyncThrottle(1, Rate.minute)],
            ),
            name='catalog',
        ),
    ],
)

urlpatterns = [router.to_urlpatterns(namespace='api')]

# run: {"method": "get", "url": "/api/catalog/", "use_urlpatterns": true}  # noqa: ERA001
# run: {"method": "get", "url": "/api/catalog/", "use_urlpatterns": true, "curl_args": ["-D", "-"], "assert-error-text": "Too many requests", "fail-with-body": false}  # noqa: ERA001, E501
