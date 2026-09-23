"""
Ready-to-use versions of everything in ``dmr.security.django_session.views``.

Every controller here is the same controller as the one
with the same name in ``dmr.security.django_session.views``,
with the default request and response bodies already plugged in.
Route one with ``as_view(serializer=...)``, there is nothing else to write.
"""

from collections.abc import Callable
from typing import Any

from django.http import HttpResponseBase
from typing_extensions import TypeVar, override

from dmr.internal.concrete import build_concrete_controller
from dmr.security.django_session import views
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)


class DjangoSessionSyncController(
    views.DjangoSessionSyncController[
        _SerializerT,
        views.DjangoSessionPayload,
        views.DjangoSessionResponse,
    ],
):
    """
    Sync controller to get a django session cookie, ready to be routed.

    Takes :class:`~dmr.security.django_session.views.DjangoSessionPayload`
    and returns
    :class:`~dmr.security.django_session.views.DjangoSessionResponse`.
    The only thing it needs is a serializer type,
    pass it to :meth:`as_view` and there is no class to write:

    .. code:: python

        path('login/', DjangoSessionSyncController.as_view(
            serializer=PydanticSerializer,
        ))

    See :class:`~dmr.security.django_session.views.DjangoSessionSyncController`
    for all the hooks it inherits, switch to it
    when the default request or response body does not fit.

    .. versionadded:: 0.16.0
    """

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | None = None,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with *serializer* filled in.

        *serializer* is required, unless a subclass already passed one
        as a type argument. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(cls, serializer=serializer)
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)

    @override
    def convert_auth_payload(
        self,
        payload: views.DjangoSessionPayload,
    ) -> views.DjangoSessionPayload:
        """Default payload is already what ``authenticate`` expects."""
        return payload

    @override
    def make_api_response(self) -> views.DjangoSessionResponse:
        """Return the id of the user we have just logged in."""
        return {'user_id': str(self.request.user.pk)}


class DjangoSessionAsyncController(
    views.DjangoSessionAsyncController[
        _SerializerT,
        views.DjangoSessionPayload,
        views.DjangoSessionResponse,
    ],
):
    """
    Async controller to get a django session cookie, ready to be routed.

    Async version of
    :class:`~dmr.security.django_session.concrete_views.DjangoSessionSyncController`.

    .. versionadded:: 0.16.0
    """

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | None = None,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with *serializer* filled in.

        *serializer* is required, unless a subclass already passed one
        as a type argument. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(cls, serializer=serializer)
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)

    @override
    async def convert_auth_payload(
        self,
        payload: views.DjangoSessionPayload,
    ) -> views.DjangoSessionPayload:
        """Default payload is already what ``aauthenticate`` expects."""
        return payload

    @override
    async def make_api_response(self) -> views.DjangoSessionResponse:
        """Return the id of the user we have just logged in."""
        return {'user_id': str((await self.request.auser()).pk)}
