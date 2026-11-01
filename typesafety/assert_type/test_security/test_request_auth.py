from typing import assert_type

from django.http import HttpRequest

from dmr.security import AsyncAuth, SyncAuth, request_auth


def auth_from_request(request: HttpRequest) -> None:
    assert_type(request_auth(request), SyncAuth | AsyncAuth | None)
    assert_type(
        request_auth(request, strict=False),
        SyncAuth | AsyncAuth | None,
    )
    assert_type(request_auth(request, strict=True), SyncAuth | AsyncAuth)
