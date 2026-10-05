from collections.abc import Callable, Sequence
from http import HTTPStatus
from typing import Any, final

import pytest
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBase
from django.views import View
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.backends import SyncDjangoCache


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    cache.clear()


class _ThrottlingMixin(View):
    """Takes ``throttling``, named like the controller attribute."""

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
        # `throttling` is read when the class is created,
        # so it can only be applied to a new subclass:
        throttled_cls: type[_ThrottlingMixin] = type(
            cls.__name__,
            (cls,),
            {'throttling': throttling, '__module__': cls.__module__},
        )
        return throttled_cls.as_view(**initkwargs)


@final
class _CatalogController(  # pyright: ignore[reportIncompatibleVariableOverride]
    Controller[PydanticSerializer],
    _ThrottlingMixin,
):
    def get(self) -> str:
        return 'inside'


def test_controller_mro() -> None:
    """Ensures that the mixin goes between the controller and the view."""
    mro = _CatalogController.__mro__

    assert mro.index(Controller) < mro.index(_ThrottlingMixin) < mro.index(View)


def test_as_view_passes_arguments(*, dmr_rf: DMRRequestFactory) -> None:
    """Ensures that the controller passes ``as_view`` arguments to mixins."""
    view = _CatalogController.as_view(
        throttling=[
            SyncThrottle(
                1,
                Rate.minute,
                backend=SyncDjangoCache(allow_unsafe_cache=True),
            ),
        ],
    )

    statuses = [view(dmr_rf.get('/whatever/')).status_code for _ in range(2)]

    assert statuses == [HTTPStatus.OK, HTTPStatus.TOO_MANY_REQUESTS]


def test_as_view_without_arguments(*, dmr_rf: DMRRequestFactory) -> None:
    """Ensures that the controller works the same without the arguments."""
    view = _CatalogController.as_view()

    responses = [view(dmr_rf.get('/whatever/')) for _ in range(2)]

    assert all(isinstance(response, HttpResponse) for response in responses)
    assert [response.status_code for response in responses] == [
        HTTPStatus.OK,
        HTTPStatus.OK,
    ]
