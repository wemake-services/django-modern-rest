import json
from collections.abc import Sequence
from http import HTTPMethod, HTTPStatus
from typing import ClassVar, Final

import pytest
from django.conf import LazySettings
from django.http import HttpResponse

from dmr import Controller, ResponseSpec, modify, validate
from dmr.exceptions import InternalServerError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import Settings
from dmr.test import DMRRequestFactory

_SERVER_ERROR: Final = frozenset((HTTPStatus.INTERNAL_SERVER_ERROR,))


class _NotExcluded(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise InternalServerError('database is down')


class _PerController(Controller[PydanticSerializer]):
    exclude_validate_responses = _SERVER_ERROR

    def get(self) -> str:
        raise InternalServerError('database is down')


class _PerEndpoint(Controller[PydanticSerializer]):
    @modify(exclude_validate_responses=_SERVER_ERROR)
    def get(self) -> str:
        raise InternalServerError('database is down')

    @validate(
        ResponseSpec(str, status_code=HTTPStatus.OK),
        exclude_validate_responses=_SERVER_ERROR,
    )
    def post(self) -> HttpResponse:
        raise InternalServerError('database is down')


def test_not_excluded_status_code(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that undescribed status codes are still errors by default."""
    request = dmr_rf.get('/whatever/')

    response = _NotExcluded.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert 'is not specified in the list' in str(response.content)


def test_per_controller(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that status codes can be excluded on controller level."""
    request = dmr_rf.get('/whatever/')
    metadata = _PerController.api_endpoints['GET'].metadata

    response = _PerController.as_view()(request)

    assert metadata.exclude_validate_responses == _SERVER_ERROR
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(response.content) == {
        'detail': [{'msg': 'Internal server error'}],
    }


@pytest.mark.parametrize('method', [HTTPMethod.GET, HTTPMethod.POST])
def test_per_endpoint(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensure that status codes can be excluded on endpoint level."""
    request = dmr_rf.generic(str(method), '/whatever/', data=None)
    metadata = _PerEndpoint.api_endpoints[str(method)].metadata

    response = _PerEndpoint.as_view()(request)

    assert metadata.exclude_validate_responses == _SERVER_ERROR
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(response.content) == {
        'detail': [{'msg': 'Internal server error'}],
    }


def test_per_settings(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensure that status codes can be excluded on settings level."""
    settings.DMR_SETTINGS = {
        Settings.exclude_validate_responses: {
            HTTPStatus.INTERNAL_SERVER_ERROR,
        },
    }

    class _PerSettings(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise InternalServerError('database is down')

    request = dmr_rf.get('/whatever/')
    metadata = _PerSettings.api_endpoints['GET'].metadata

    response = _PerSettings.as_view()(request)

    assert metadata.exclude_validate_responses == _SERVER_ERROR
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_overrides(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensure that excluded status codes can be reset back."""
    settings.DMR_SETTINGS = {
        Settings.exclude_validate_responses: {
            HTTPStatus.INTERNAL_SERVER_ERROR,
        },
    }

    class _PerSettings(Controller[PydanticSerializer]):
        exclude_validate_responses = frozenset((HTTPStatus.NOT_FOUND,))

        @modify(exclude_validate_responses=None)
        def get(self) -> str:
            raise InternalServerError('database is down')

    request = dmr_rf.get('/whatever/')
    metadata = _PerSettings.api_endpoints['GET'].metadata

    response = _PerSettings.as_view()(request)

    assert metadata.exclude_validate_responses == frozenset()
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class _StillValidated(Controller[PydanticSerializer]):
    exclude_validate_responses = _SERVER_ERROR

    def get(self) -> list[str]:
        return [1, 2]  # type: ignore[list-item]


def test_other_status_codes_are_validated(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that excluding one status code does not disable the rest."""
    request = dmr_rf.get('/whatever/')

    response = _StillValidated.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class _WronglyDescribed(Controller[PydanticSerializer]):
    exclude_validate_responses = _SERVER_ERROR

    # Our errors are not lists of integers,
    # but we don't validate this status code anymore:
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(list[int], status_code=HTTPStatus.INTERNAL_SERVER_ERROR),
    )

    def get(self) -> str:
        raise InternalServerError('database is down')


def test_excluded_status_code_skips_body(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that excluded status codes skip the body validation as well."""
    request = dmr_rf.get('/whatever/')

    response = _WronglyDescribed.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
