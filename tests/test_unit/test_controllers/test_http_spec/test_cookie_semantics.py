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

_SECURE_WHEN_SAMESITE_NONE: Final[str] = (
    "Cookie with samesite='none' requires secure to be True"
)
_COOKIE_AGE_NOT_NEGATIVE: Final[str] = 'Cookie max age must not be negative'
_SECURE_PREFIX_REQUIREMENTS: Final[str] = (
    '__Secure- cookie prefix requires secure to be True'
)
_HOST_PREFIX_REQUIREMENTS: Final[str] = (
    '__Host- cookie prefix requires secure to be True, '
    'path set to / and domain to be None'
)


class _UserModel(pydantic.BaseModel):
    username: str


def test_secure_when_samesite_none() -> None:
    """Ensure that when samesite='none' secure must be True."""
    cookies = {'session_id': CookieSpec(samesite='none', secure=False)}

    with pytest.raises(
        EndpointMetadataError,
        match=_SECURE_WHEN_SAMESITE_NONE,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    status_code=HTTPStatus.OK,
                    cookies=cookies,
                    return_type=None,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_max_age_not_negative() -> None:
    """Ensure that max_age cannot be negative."""
    cookies = {
        'session_id': CookieSpec(samesite='none', secure=True, max_age=-100),
    }

    with pytest.raises(
        EndpointMetadataError,
        match=_COOKIE_AGE_NOT_NEGATIVE,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    status_code=HTTPStatus.OK,
                    cookies=cookies,
                    return_type=None,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_secure_prefix_requirements() -> None:
    """Ensure that when __Secure- prefix cookies follow required parameters."""
    cookies = {
        '__Secure-Token': CookieSpec(samesite='lax', secure=False, max_age=100),
    }

    with pytest.raises(
        EndpointMetadataError,
        match=_SECURE_PREFIX_REQUIREMENTS,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    status_code=HTTPStatus.OK,
                    cookies=cookies,
                    return_type=None,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


@pytest.mark.parametrize(
    'cookie_spec',
    [
        CookieSpec(secure=False, path='/', domain=None),
        CookieSpec(secure=True, path='/somwhere', domain=None),
        CookieSpec(secure=True, path='/', domain='user'),
    ],
)
def test_host_prefix_requirements(cookie_spec: CookieSpec) -> None:
    """Ensure that when __Host- prefix cookies follow required parameters."""
    cookies = {'__Host-Token': cookie_spec}

    with pytest.raises(
        EndpointMetadataError,
        match=_HOST_PREFIX_REQUIREMENTS,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    status_code=HTTPStatus.OK,
                    cookies=cookies,
                    return_type=None,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_cookie_semantic_validation_in_modify() -> None:
    """Ensure that cookie semantic validation works in modify."""
    cookies = {
        'session_id': NewCookie(samesite='none', secure=False, value='1'),
    }

    with pytest.raises(
        EndpointMetadataError,
        match=_SECURE_WHEN_SAMESITE_NONE,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @modify(
                cookies=cookies,
            )
            def get(self) -> _UserModel:
                raise NotImplementedError


def test_check_cookie_semantics_controller() -> None:
    """Ensure that the validation can be disabled on controller level."""
    cookies = {
        'session_id': NewCookie(samesite='none', secure=False, value='1'),
    }

    class _Mixed(Controller[PydanticSerializer]):
        @modify(
            cookies=cookies,
            no_validate_http_spec={HttpSpec.cookie_semantics},
        )
        def get(self) -> _UserModel:
            raise NotImplementedError
