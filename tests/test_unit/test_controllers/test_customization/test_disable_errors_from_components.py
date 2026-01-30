import json
from http import HTTPMethod, HTTPStatus
from typing import Any, final

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse

from django_modern_rest import Controller, ResponseSpec, modify, validate
from django_modern_rest.components import Body
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security import DjangoSessionSyncAuth
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _WrongController(Controller[PydanticSerializer]):
    """All return types of these methods are not correct."""

    enable_semantic_responses = False

    def get(self) -> str:
        return 1  # type: ignore[return-value]

    @modify(status_code=HTTPStatus.OK)
    def post(self) -> int:
        return 'missing'  # type: ignore[return-value]

    @validate(
        ResponseSpec(
            return_type=dict[str, int],
            status_code=HTTPStatus.OK,
        ),
    )
    def patch(self) -> HttpResponse:
        return HttpResponse(b'[]')


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PATCH,
    ],
)
def test_responses_are_not_added_decorators(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response validation works for default settings."""
    endpoint = _WrongController.api_endpoints[str(method)]
    assert len(endpoint.metadata.responses) == 1

    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WrongController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content)['detail']


@final
class _GlobalDisable(Controller[PydanticSerializer], Body[list[int]]):
    enable_semantic_responses = False
    auth = [DjangoSessionSyncAuth()]

    def post(self) -> str:
        raise NotImplementedError


@pytest.mark.parametrize(
    ('request_kwargs', 'user'),
    [
        ({'body': b'[]'}, AnonymousUser()),  # missing auth
        ({}, User()),  # missing request body
    ],
)
def test_responses_are_not_added_global(
    dmr_rf: DMRRequestFactory,
    *,
    request_kwargs: dict[str, Any],
    user: User | AnonymousUser,
) -> None:
    """Ensures that semantic responses are not added globally."""
    assert len(_GlobalDisable.api_endpoints['POST'].metadata.responses) == 1

    request = dmr_rf.post('/whatever/', **request_kwargs)
    request.user = user

    response = _GlobalDisable.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    # Response code changes from 400 and 401 to 422:
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert (
        'is not specified in the list' in json.loads(response.content)['detail']
    )


@final
class _ModifyDisable(Controller[PydanticSerializer], Body[list[int]]):
    @modify(enable_semantic_responses=False, auth=[DjangoSessionSyncAuth()])
    def post(self) -> str:
        raise NotImplementedError


@final
class _ValidateDisable(Controller[PydanticSerializer], Body[list[int]]):
    @validate(
        ResponseSpec(
            return_type=list[str],
            status_code=HTTPStatus.OK,
        ),
        enable_semantic_responses=False,
        auth=[DjangoSessionSyncAuth()],
    )
    def post(self) -> HttpResponse:
        raise NotImplementedError


@pytest.mark.parametrize('controller', [_ModifyDisable, _ValidateDisable])
@pytest.mark.parametrize(
    ('request_kwargs', 'user', 'response_status'),
    [
        # Auth was not added:
        ({'body': b'[]'}, AnonymousUser(), HTTPStatus.UNPROCESSABLE_ENTITY),
        # But validation was:
        ({}, User(), HTTPStatus.BAD_REQUEST),
    ],
)
def test_responses_are_not_added_modify(
    dmr_rf: DMRRequestFactory,
    *,
    controller: type[Controller[BaseSerializer]],
    request_kwargs: dict[str, Any],
    user: User | AnonymousUser,
    response_status: HTTPStatus,
) -> None:
    """Ensures that semantic responses are not added in modify."""
    assert len(controller.api_endpoints['POST'].metadata.responses) == 2

    request = dmr_rf.post('/whatever/', **request_kwargs)
    request.user = user

    response = controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == response_status
    assert json.loads(response.content)['detail']
