from http import HTTPMethod, HTTPStatus
from typing import Final

import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse

from dmr import Controller, ResponseSpec, modify, validate
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import JWTSyncAuth
from dmr.settings import Settings

_MATCH_PATTERN: Final = 'cannot have a request body'


class _BodyModel(pydantic.BaseModel):
    name: str


class _PerController(Controller[PydanticSerializer]):
    auth = (JWTSyncAuth(),)
    exclude_semantic_responses = frozenset((HTTPStatus.UNAUTHORIZED,))

    def get(self) -> str:
        raise NotImplementedError


def test_exclude_semantic_responses_controller() -> None:
    """Ensure that responses can be disabled on controller level."""
    metadata = _PerController.api_endpoints['GET'].metadata

    assert metadata.exclude_semantic_responses == frozenset((
        HTTPStatus.UNAUTHORIZED,
    ))
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses


class _PerEndpoint(Controller[PydanticSerializer]):
    auth = (JWTSyncAuth(),)

    @modify(exclude_semantic_responses={HTTPStatus.UNAUTHORIZED})
    def get(self) -> str:
        raise NotImplementedError

    @validate(
        ResponseSpec(str, status_code=HTTPStatus.OK),
        exclude_semantic_responses={HTTPStatus.UNAUTHORIZED},
    )
    def post(self) -> HttpResponse:
        raise NotImplementedError


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
    ],
)
def test_exclude_semantic_responses_endpoint(
    *,
    method: HTTPMethod,
) -> None:
    """Ensure that responses can be disabled on endpoint level."""
    metadata = _PerEndpoint.api_endpoints[str(method)].metadata

    assert metadata.exclude_semantic_responses == frozenset((
        HTTPStatus.UNAUTHORIZED,
    ))
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses


def test_exclude_semantic_responses_settings(settings: LazySettings) -> None:
    """Ensure that responses can be disabled on settings level."""
    settings.DMR_SETTINGS = {
        Settings.exclude_semantic_responses: {HTTPStatus.UNAUTHORIZED},
    }

    class _PerSettings(Controller[PydanticSerializer]):
        auth = (JWTSyncAuth(),)

        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerSettings.api_endpoints['GET'].metadata

    assert metadata.exclude_semantic_responses == frozenset((
        HTTPStatus.UNAUTHORIZED,
    ))
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED not in metadata.responses


def test_exclude_semantic_responses_overrides(settings: LazySettings) -> None:
    """Ensure that responses override."""
    settings.DMR_SETTINGS = {
        Settings.exclude_semantic_responses: {HTTPStatus.UNAUTHORIZED},
    }

    class _PerSettings(Controller[PydanticSerializer]):
        auth = (JWTSyncAuth(),)
        exclude_semantic_responses = frozenset((
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ))

        @modify(exclude_semantic_responses=None)
        def get(self) -> str:
            raise NotImplementedError

    metadata = _PerSettings.api_endpoints['GET'].metadata

    assert metadata.exclude_semantic_responses == frozenset()
    assert HTTPStatus.OK in metadata.responses
    assert HTTPStatus.UNAUTHORIZED in metadata.responses
