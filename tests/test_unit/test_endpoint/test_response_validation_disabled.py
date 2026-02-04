import json
from http import HTTPMethod, HTTPStatus
from typing import ClassVar, final

import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot

from django_modern_rest import (
    Blueprint,
    Controller,
    HeaderSpec,
    ResponseSpec,
    modify,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.settings import Settings
from django_modern_rest.test import DMRRequestFactory


@pytest.fixture(autouse=True)
def _disable_response_validation(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    settings.DMR_SETTINGS = {
        Settings.validate_responses: False,
    }


@final
class _MyPydanticModel(pydantic.BaseModel):
    email: str


@final
class _WrongController(Controller[PydanticSerializer]):
    """All return types of these methods are not correct."""

    def get(self) -> _MyPydanticModel:
        """Does not respect an annotation type."""
        return 1  # type: ignore[return-value]

    @validate(
        ResponseSpec(return_type=list[int], status_code=HTTPStatus.OK),
    )
    def post(self) -> HttpResponse:
        """Does not respect a `return_type` validator."""
        return HttpResponse(b'1')

    @modify(status_code=HTTPStatus.OK)
    def put(self) -> list[int]:
        """Does not respect the annotation with `@modify`."""
        return 1  # type: ignore[return-value]


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PUT,
    ],
)
def test_validate_response_disabled(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response validation can be disabled."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WrongController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == 1


@final
class _WrongStatusCodeController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            return_type=list[int],
            status_code=HTTPStatus.CREATED,
        ),
    )
    def get(self) -> HttpResponse:
        """Does not respect a `status_code` validator."""
        return HttpResponse(b'[]', status=HTTPStatus.OK)


def test_validate_status_code(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.get('/whatever/')

    response = _WrongStatusCodeController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == []


@final
class _WrongHeadersController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            return_type=list[int],
            status_code=HTTPStatus.CREATED,
            headers={'X-Token': HeaderSpec()},
        ),
    )
    def post(self) -> HttpResponse:
        """Does not respect a `headers` validator."""
        return self.to_response([])


def test_validate_headers(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.post('/whatever/')

    response = _WrongHeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == []


@final
class _ValidatedEndpointController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            return_type=list[int],
            status_code=HTTPStatus.CREATED,
        ),
        validate_responses=True,
    )
    def post(self) -> HttpResponse:
        return self.to_response(['a'])  # list[str]


def test_override_endpoint_validation(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that endpoints can override global validation configuration."""
    request = dmr_rf.post('/whatever/')

    response = _ValidatedEndpointController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be a valid integer',
                'loc': ['0'],
                'type': 'value_error',
            },
        ],
    })


@final
class _ValidatedController(Controller[PydanticSerializer]):
    validate_responses: ClassVar[bool | None] = True

    @validate(
        ResponseSpec(
            return_type=list[int],
            status_code=HTTPStatus.CREATED,
        ),
    )
    def post(self) -> HttpResponse:
        return self.to_response(['a'])  # list[str]

    @validate(
        ResponseSpec(
            return_type=list[int],
            status_code=HTTPStatus.OK,
        ),
        validate_responses=True,
    )
    def put(self) -> HttpResponse:
        return self.to_response(['a'])  # list[str]


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
    ],
)
def test_override_controller_validation(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that controllers can override global validation configuration."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _ValidatedController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be a valid integer',
                'loc': ['0'],
                'type': 'value_error',
            },
        ],
    })


@final
class _EndpointOverController(Controller[PydanticSerializer]):
    validate_responses: ClassVar[bool | None] = False

    @modify(validate_responses=True)  # takes priority
    def post(self) -> list[int]:
        return ['a']  # type: ignore[list-item]


def test_override_endpoint_over_controller(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that endpoints have a prioriry over controller."""
    request = dmr_rf.post('/whatever/')

    response = _EndpointOverController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be a valid integer',
                'loc': ['0'],
                'type': 'value_error',
            },
        ],
    })


@final
class _NonValidatedBlueprint(Blueprint[PydanticSerializer]):
    validate_responses: ClassVar[bool | None] = False

    def post(self) -> list[int]:
        return ['a']  # type: ignore[list-item]


@final
class _BlueprintOverController(Controller[PydanticSerializer]):
    validate_responses: ClassVar[bool | None] = True  # blueprint overrides

    blueprints = (_NonValidatedBlueprint,)


def test_override_blueprint_over_controller(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that blueprints have a prioriry over controller."""
    request = dmr_rf.post('/whatever/')

    response = _BlueprintOverController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == snapshot(['a'])


@final
class _ValidatedBlueprint(Blueprint[PydanticSerializer]):
    validate_responses: ClassVar[bool | None] = False

    @modify(validate_responses=True)
    def post(self) -> list[int]:
        return ['a']  # type: ignore[list-item]


@final
class _EndpointOverBlueprint(Controller[PydanticSerializer]):
    validate_responses: ClassVar[bool | None] = False  # overridden

    blueprints = (_ValidatedBlueprint,)


def test_override_endpoint_over_blueprint(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that endpoints have a prioriry over blueprints."""
    request = dmr_rf.post('/whatever/')

    response = _EndpointOverBlueprint.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be a valid integer',
                'loc': ['0'],
                'type': 'value_error',
            },
        ],
    })
