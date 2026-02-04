import json
from http import HTTPMethod, HTTPStatus
from typing import ClassVar, TypeAlias, final

import pydantic
import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from django_modern_rest import Controller, ResponseSpec, modify, validate
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _MyPydanticModel(pydantic.BaseModel):
    email: str


@final
class _MyTypedDict(TypedDict):
    missing: str


@final
class _WrongController(Controller[PydanticSerializer]):
    """All return types of these methods are not correct."""

    def get(self) -> str:
        """Does not respect a simple builtin type."""
        return 1  # type: ignore[return-value]

    def post(self) -> list[str]:
        """Does not respect a generic builtin type."""
        return [1, 2]  # type: ignore[list-item]

    @modify(status_code=HTTPStatus.OK)
    def put(self) -> _MyTypedDict:
        """Does not respect a TypedDict type."""
        return {'missing': 1}  # type: ignore[typeddict-item]

    def patch(self) -> _MyPydanticModel:
        """Does not respect a pydantic model type."""
        return {'wrong': 'abc'}  # type: ignore[return-value]

    @validate(
        ResponseSpec(
            return_type=dict[str, int],
            status_code=HTTPStatus.OK,
        ),
    )
    def delete(self) -> HttpResponse:
        """Does not respect a `return_type` validator."""
        return HttpResponse(b'[]')


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
        HTTPMethod.DELETE,
    ],
)
def test_validate_response(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response validation works for default settings."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WrongController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content)['detail'][0]['type'] == 'value_error'


def test_validate_response_text(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that response validation works for default settings."""
    request = dmr_rf.get('/whatever/')

    response = _WrongController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be a valid string',
                'loc': [],
                'type': 'value_error',
            },
        ],
    })


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
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Returned status_code=200 is not specified '
                    'in the list of allowed codes {<HTTPStatus.CREATED: 201>, '
                    '<HTTPStatus.NOT_ACCEPTABLE: 406>}'
                ),
                'type': 'value_error',
            },
        ],
    })


_ListOfInts: TypeAlias = list[int]


@final
class _StringifiedController(Controller[PydanticSerializer]):
    def get(self) -> '_ListOfInts':
        """Needs to solve the string annotation correctly."""
        return [1, 2]


def test_solve_string_annotation_for_endpoint(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.get('/whatever/')

    response = _StringifiedController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == [1, 2]


@final
class _WeakTypeController(Controller[PydanticSerializer]):
    """All return types of these methods are not correct without coercing."""

    def post(self) -> list[int]:
        """Does not respect a generic builtin type."""
        return ['1', '2']  # type: ignore[list-item]


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
    ],
)
def test_weak_type_response_validation(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures weak type response validation does not work."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WeakTypeController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be a valid integer',
                'loc': ['0'],
                'type': 'value_error',
            },
            {
                'msg': 'Input should be a valid integer',
                'loc': ['1'],
                'type': 'value_error',
            },
        ],
    })


@final
class _EndpointDisabledController(Controller[PydanticSerializer]):
    @modify(validate_responses=False)
    def post(self) -> list[int]:
        return ['a']  # type: ignore[list-item]


def test_validation_disabled_endpoint(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that endpoints can disable validation."""
    request = dmr_rf.post('/whatever/')

    response = _EndpointDisabledController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == ['a']


@final
class _ValidationDisabledController(Controller[PydanticSerializer]):
    validate_responses: ClassVar[bool | None] = False

    def post(self) -> list[int]:
        return ['a']  # type: ignore[list-item]


def test_validation_disabled_controller(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that controllers can disable validation."""
    request = dmr_rf.post('/whatever/')

    response = _ValidationDisabledController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == ['a']


@final
class _ModelWithFieldValidator(pydantic.BaseModel):
    username: str

    @pydantic.field_validator('username', mode='before')
    @classmethod
    def validate_username(cls, username: str) -> str:
        # prefix "validated-" to the username for each validation
        return f'validated-{username}'


@final
class _ValidateController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            return_type=_ModelWithFieldValidator,
            status_code=HTTPStatus.OK,
        ),
    )
    def get(self) -> HttpResponse:
        return HttpResponse(
            json.dumps(
                _ModelWithFieldValidator(username='admin').model_dump(),
            ),
        )


def test_double_validation_with_validate(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that @validate does not cause double validation."""
    request = dmr_rf.get('/whatever/')

    response = _ValidateController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'username': 'validated-admin'}


@final
class _ModifyWithValidationController(
    Controller[PydanticSerializer],
):
    @modify(
        status_code=HTTPStatus.OK,
        validate_responses=True,
    )
    def get(self) -> _ModelWithFieldValidator:
        return _ModelWithFieldValidator(username='admin')


def test_double_validation_modify_with_validation(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that @modify with validation does not cause double validation."""
    request = dmr_rf.get('/whatever/')

    response = _ModifyWithValidationController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'username': 'validated-admin'}


@final
class _ModifyWithValidationRawDataController(
    Controller[PydanticSerializer],
):
    @modify(
        status_code=HTTPStatus.OK,
        validate_responses=True,
    )
    def get(self) -> _ModelWithFieldValidator:
        return {'username': 'admin'}  # type: ignore[return-value]


def test_double_validation_modify_raw_data(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that @modify with raw data does not cause double validation."""
    request = dmr_rf.get('/whatever/')

    response = _ModifyWithValidationRawDataController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'username': 'admin'}


@final
class _ModifyNoValidationController(
    Controller[PydanticSerializer],
):
    @modify(
        status_code=HTTPStatus.OK,
        validate_responses=False,
    )
    def get(self) -> _ModelWithFieldValidator:
        return _ModelWithFieldValidator(username='admin')


def test_double_validation_modify_no_validation(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that @modify without validation performs zero validations."""
    request = dmr_rf.get('/whatever/')

    response = _ModifyNoValidationController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'username': 'validated-admin'}


@final
class _RawPydanticReturnController(
    Controller[PydanticSerializer],
):
    def get(self) -> _ModelWithFieldValidator:
        return _ModelWithFieldValidator(username='admin')


def test_double_validation_pydantic_model_return(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that Pydantic model return does not cause double validation."""
    request = dmr_rf.get('/whatever/')

    response = _RawPydanticReturnController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'username': 'validated-admin'}


@final
class _RawDictReturnController(Controller[PydanticSerializer]):
    def get(self) -> _ModelWithFieldValidator:
        return {'username': 'admin'}  # type: ignore[return-value]


def test_double_validation_raw_dict_return(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that returning raw data does not cause double validation."""
    request = dmr_rf.get('/whatever/')

    response = _RawDictReturnController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'username': 'admin'}
