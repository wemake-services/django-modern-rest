from datetime import UTC, datetime
from http import HTTPStatus
from types import MappingProxyType
from typing import Final, final

import pydantic
from django.http import Http404, HttpRequest, HttpResponse
from django.urls import path
from django.views.decorators.http import condition

from dmr import Controller, HeaderSpec, Path, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.plugins.pydantic import PydanticSerializer


@final
class _UserModel(pydantic.BaseModel):
    user_id: int
    updated_at: datetime
    message: str


@final
class _PathModel(pydantic.BaseModel):
    user_id: int


@final
class _ResponseModel(pydantic.BaseModel):
    message: str
    updated_at: str


# Imitate DB
_USERS: Final = MappingProxyType({
    1: _UserModel(
        user_id=1,
        updated_at=datetime(2026, 3, 23, 12, 30, tzinfo=UTC),  # noqa: WPS432
        message='Fresh content for user #1',
    ),
    2: _UserModel(
        user_id=2,
        updated_at=datetime(2026, 3, 24, 9, 15, tzinfo=UTC),  # noqa: WPS432
        message='Fresh content for user #2',
    ),
})


def _build_etag(user: _UserModel) -> str:
    updated_at = user.updated_at.isoformat()
    return f'"user-{user.user_id}-{updated_at}"'


def _etag(request: HttpRequest, user_id: int = 0, **_: object) -> str | None:
    user = _USERS.get(user_id)
    return _build_etag(user) if user else None


@wrap_middleware(
    condition(etag_func=_etag),
    ResponseSpec(return_type=_ResponseModel, status_code=HTTPStatus.OK),
    ResponseSpec(
        return_type=None,
        status_code=HTTPStatus.NOT_MODIFIED,
        headers={'ETag': HeaderSpec()},
    ),
)
def _condition_middleware(response: HttpResponse) -> HttpResponse:
    """Adds Content-Type for 304 responses to satisfy strict validation."""
    if response.status_code == HTTPStatus.NOT_MODIFIED:
        response.headers['Content-Type'] = 'application/json'
    return response


@final
@_condition_middleware
class ConditionalETagController(
    Controller[PydanticSerializer],
    Path[_PathModel],
):
    responses = _condition_middleware.responses

    def get(self) -> HttpResponse:
        user_id = self.parsed_path.user_id
        user = _USERS.get(user_id)
        if user is None:
            raise Http404(f'User {user_id} not found')
        return self.to_response(
            _ResponseModel(
                message=user.message,
                updated_at=user.updated_at.isoformat(),
            ),
        )


urlpatterns = [
    path('api/etag/<int:user_id>/', ConditionalETagController.as_view()),
]

# run: {"controller": "ConditionalETagController", "method": "get", "url": "/api/etag/1/", "use_urlpatterns": true, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# run: {"controller": "ConditionalETagController", "method": "get", "url": "/api/etag/1/", "use_urlpatterns": true, "headers": {"If-None-Match": "\"user-1-2026-03-23T12:30:00+00:00\""}, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "ConditionalETagController", "method": "get", "url": "/api/etag/2/", "use_urlpatterns": true, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
