import datetime as dt
from typing import assert_type

from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest

from dmr.security.token import TokenLikeAsync, TokenLikeSync, request_token
from dmr.security.token.app.models import Token


def accepts_token(token: Token) -> None:
    assert_type(token.user, AbstractBaseUser)  # pyrefly: ignore[assert-type]
    assert_type(token.name, str)
    assert_type(token.token_hash, str)
    assert_type(token.expires_at, dt.datetime | None)
    assert_type(token.revoked_at, dt.datetime | None)
    assert_type(token.last_used_at, dt.datetime | None)
    assert_type(token.created_at, dt.datetime)
    assert_type(token.updated_at, dt.datetime)


def token_from_request(request: HttpRequest) -> None:
    assert_type(request_token(request), TokenLikeSync | None)
    assert_type(request_token(request, strict=True), TokenLikeSync)
    assert_type(request_token(request, sync=False), TokenLikeAsync | None)
    assert_type(request_token(request, sync=False, strict=True), TokenLikeAsync)
