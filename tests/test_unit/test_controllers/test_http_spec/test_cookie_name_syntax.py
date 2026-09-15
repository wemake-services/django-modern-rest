import re
from http import HTTPStatus
from typing import Final

import pydantic
import pytest
from django.http import HttpResponse

from dmr import (
    Controller,
    CookieSpec,
    NewCookie,
    ResponseSpec,
    modify,
    validate,
)
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer

_MATCH_PATTERN: Final = re.compile(
    r'\b(Cookie|Header)\b name .+ is not following http spec',
)


class _UserModel(pydantic.BaseModel):
    username: str


@pytest.mark.parametrize(
    'cookie',
    ['user name', 'auth,token', 'cookie[test], my(cookie)'],
)
def test_check_cookie_name_syntax(
    *,
    cookie: str,
) -> None:
    """Ensure that response cookies' names follow http spec syntax."""
    with pytest.raises(
        EndpointMetadataError,
        match=_MATCH_PATTERN,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    status_code=HTTPStatus.OK,
                    cookies={cookie: CookieSpec()},
                    return_type=None,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


@pytest.mark.parametrize(
    'cookie',
    ['user name', 'auth,token', 'cookie[test], my(cookie)'],
)
def test_check_new_cookie_name_syntax(
    *,
    cookie: str,
) -> None:
    """Ensure that new cookies' names follow http spec syntax."""
    with pytest.raises(
        EndpointMetadataError,
        match=_MATCH_PATTERN,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @modify(
                cookies={cookie: NewCookie(value='1')},
            )
            def get(self) -> _UserModel:
                raise NotImplementedError
