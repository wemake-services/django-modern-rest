import types
from collections.abc import Iterator
from typing import Any, Final, final

import pytest
from django.http import HttpRequest
from django.views.debug import SafeExceptionReporterFilter
from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session.views import (
    DjangoSessionAsyncController,
    DjangoSessionPayload,
    DjangoSessionResponse,
    DjangoSessionSyncController,
)
from dmr.security.jwt.views import (
    ObtainTokensResponse,
    RefreshTokenAsyncController,
    RefreshTokenPayload,
    RefreshTokenSyncController,
)
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_SECRET: Final = 'do-not-leak-me'  # noqa: S105
_CLEANSED: Final = SafeExceptionReporterFilter.cleansed_substitute

_SESSION_VIEWS: Final = DjangoSessionSyncController.__module__
_JWT_VIEWS: Final = RefreshTokenSyncController.__module__


class _BoomError(Exception):
    """Raised from the auth views to inspect their tracebacks."""


@final
class _SessionSyncController(
    DjangoSessionSyncController[
        PydanticSerializer,
        DjangoSessionPayload,
        DjangoSessionResponse,
    ],
):
    @override
    def convert_auth_payload(
        self,
        payload: DjangoSessionPayload,
    ) -> DjangoSessionPayload:
        raise _BoomError

    @override
    def make_api_response(self) -> DjangoSessionResponse:
        raise NotImplementedError


@final
class _SessionAsyncController(
    DjangoSessionAsyncController[
        PydanticSerializer,
        DjangoSessionPayload,
        DjangoSessionResponse,
    ],
):
    @override
    async def convert_auth_payload(
        self,
        payload: DjangoSessionPayload,
    ) -> DjangoSessionPayload:
        raise _BoomError

    @override
    async def make_api_response(self) -> DjangoSessionResponse:
        raise NotImplementedError


@final
class _RefreshSyncController(
    RefreshTokenSyncController[
        PydanticSerializer,
        RefreshTokenPayload,
        ObtainTokensResponse,
    ],
):
    @override
    def convert_refresh_payload(self, payload: RefreshTokenPayload) -> str:
        raise _BoomError

    @override
    def make_api_response(self) -> ObtainTokensResponse:
        raise NotImplementedError


@final
class _RefreshAsyncController(
    RefreshTokenAsyncController[
        PydanticSerializer,
        RefreshTokenPayload,
        ObtainTokensResponse,
    ],
):
    @override
    async def convert_refresh_payload(
        self,
        payload: RefreshTokenPayload,
    ) -> str:
        raise _BoomError

    @override
    async def make_api_response(self) -> ObtainTokensResponse:
        raise NotImplementedError


def _traceback_frames(error: BaseException) -> Iterator[types.FrameType]:
    traceback = error.__traceback__
    while traceback is not None:
        yield traceback.tb_frame
        traceback = traceback.tb_next


def _cleansed_locals(
    request: HttpRequest,
    frame: types.FrameType,
) -> dict[str, Any]:
    reporter_filter = SafeExceptionReporterFilter()
    return dict(reporter_filter.get_traceback_frame_variables(request, frame))


def _view_frames(
    request: HttpRequest,
    error: BaseException,
    module: str,
) -> dict[str, dict[str, Any]]:
    """Cleansed locals of all *module* frames found in the traceback."""
    return {
        frame.f_code.co_name: _cleansed_locals(request, frame)
        for frame in _traceback_frames(error)
        if frame.f_globals.get('__name__') == module
    }


def _leaking_frames(request: HttpRequest, error: BaseException) -> list[str]:
    """Names of all frames that still show the secret in error reports."""
    return [
        frame.f_code.co_name
        for frame in _traceback_frames(error)
        if _SECRET in repr(_cleansed_locals(request, frame))
    ]


def test_sync_session_login_hides_credentials(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures sync session login never shows credentials in error reports."""
    request = dmr_rf.post(
        '/login/',
        data={'username': 'someone', 'password': _SECRET},
        content_type='application/json',
    )

    with pytest.raises(_BoomError) as exc_info:
        _SessionSyncController.as_view()(request)
    error = exc_info.value  # noqa: WPS441

    frames = _view_frames(request, error, _SESSION_VIEWS)
    assert frames['post']['parsed_body'] == _CLEANSED
    assert frames['login']['parsed_body'] == _CLEANSED
    assert not _leaking_frames(request, error)


async def test_async_session_login_hides_credentials(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures async session login hides credentials in its own frames."""
    request = dmr_async_rf.post(
        '/login/',
        data={'username': 'someone', 'password': _SECRET},
        content_type='application/json',
    )

    with pytest.raises(_BoomError) as exc_info:
        await dmr_async_rf.wrap(_SessionAsyncController.as_view()(request))
    error = exc_info.value  # noqa: WPS441

    frames = _view_frames(request, error, _SESSION_VIEWS)
    assert frames['post']['parsed_body'] == _CLEANSED
    assert frames['login']['parsed_body'] == _CLEANSED


def test_sync_refresh_hides_tokens(dmr_rf: DMRRequestFactory) -> None:
    """Ensures sync jwt refresh never shows tokens in error reports."""
    request = dmr_rf.post(
        '/refresh/',
        data={'refresh_token': _SECRET},
        content_type='application/json',
    )

    with pytest.raises(_BoomError) as exc_info:
        _RefreshSyncController.as_view()(request)
    error = exc_info.value  # noqa: WPS441

    frames = _view_frames(request, error, _JWT_VIEWS)
    assert frames['post']['parsed_body'] == _CLEANSED
    assert frames['refresh']['parsed_body'] == _CLEANSED
    assert not _leaking_frames(request, error)


async def test_async_refresh_hides_tokens(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures async jwt refresh hides tokens in its own frames."""
    request = dmr_async_rf.post(
        '/refresh/',
        data={'refresh_token': _SECRET},
        content_type='application/json',
    )

    with pytest.raises(_BoomError) as exc_info:
        await dmr_async_rf.wrap(_RefreshAsyncController.as_view()(request))
    error = exc_info.value  # noqa: WPS441

    frames = _view_frames(request, error, _JWT_VIEWS)
    assert frames['post']['parsed_body'] == _CLEANSED
    assert frames['refresh']['parsed_body'] == _CLEANSED
