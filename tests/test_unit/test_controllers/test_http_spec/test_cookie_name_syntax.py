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
from dmr.settings import HttpSpec

_MATCH_PATTERN: Final = re.compile(
    r'Cookie name .+ is not following http spec.',
)


class _UserModel(pydantic.BaseModel):
    username: str


@pytest.mark.parametrize(
    'cookie',
    ['user name', 'auth,token', 'cookie[test], my(cookie)'],
)
def test_check_cookie_name_syntax(
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


def test_check_cookie_name_syntax_controller() -> None:
    """Ensure that the validation can be disabled on controller level."""

    class _Mixed(Controller[PydanticSerializer]):
        @modify(
            cookies={'user name': NewCookie(value='1')},
            no_validate_http_spec={HttpSpec.cookie_name_syntax},
        )
        def get(self) -> _UserModel:
            raise NotImplementedError
