import contextlib
import dataclasses
from collections.abc import Generator
from typing import TYPE_CHECKING

from django.http import HttpRequest

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.security import AsyncAuth, SyncAuth
    from dmr.serializer import BaseSerializer


@contextlib.contextmanager
def disabled_auth(
    controller_cls: type['Controller[BaseSerializer]'],
    *,
    request: HttpRequest,
    user: 'AbstractBaseUser',
    auth: 'SyncAuth | AsyncAuth | None' = None,
) -> Generator[None]:
    """
    Temporarily disable all auth for the endpoint for testing.

    Parameters:
        controller_cls: Controller whose endpoint is under test.
        request: HTTP method of the endpoint to target.
        user: User to be used for this request.
        auth: Optional auth instance to be used for this request.
            It is set as ``__dmr_auth__`` attribute, like our regular auth does.
            Use :func:`dmr.security.request_auth` to get it from request.

    .. versionadded:: 0.13.0
    """
    endpoint = _get_endpoint(controller_cls, request)
    metadata = endpoint.metadata
    if not metadata.auth:
        raise ValueError(
            f'Endpoint {metadata.operation_id} has no auth to override',
        )

    # Asign required props:
    _set_request_attrs(controller_cls, request=request, user=user, auth=auth)

    # Clear the auth, restore it later:
    endpoint.metadata = dataclasses.replace(metadata, auth=None)
    try:
        yield
    finally:
        endpoint.metadata = metadata


def _get_endpoint(
    controller_cls: type['Controller[BaseSerializer]'],
    request: HttpRequest,
) -> 'Endpoint':
    method: str = request.method  # type: ignore[assignment]
    endpoint = controller_cls.api_endpoints.get(method.upper())
    if endpoint is None:
        raise ValueError(
            f'{controller_cls.__qualname__} has no endpoint '
            f'for method {method!r}',
        )
    return endpoint


def _set_request_attrs(
    controller_cls: type['Controller[BaseSerializer]'],
    *,
    request: HttpRequest,
    user: 'AbstractBaseUser',
    auth: 'SyncAuth | AsyncAuth | None',
) -> None:
    from dmr.security import AsyncAuth, SyncAuth  # noqa: PLC0415
    from dmr.security.token.request import set_request_attrs  # noqa: PLC0415

    set_request_attrs(request, user)
    if auth is None:
        return
    if controller_cls.is_async and isinstance(auth, SyncAuth):
        raise ValueError(
            f'Using sync auth {auth} '
            f'for async controller {controller_cls.__qualname__}',
        )
    if not controller_cls.is_async and isinstance(auth, AsyncAuth):
        raise ValueError(
            f'Using async auth {auth} '
            f'for sync controller {controller_cls.__qualname__}',
        )
    request.__dmr_auth__ = auth  # type: ignore[attr-defined]
