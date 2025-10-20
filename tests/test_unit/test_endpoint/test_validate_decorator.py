import json
from http import HTTPMethod, HTTPStatus
from typing import Generic, Literal, TypeVar, final

import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from django_modern_rest import (
    Controller,
    HeaderDescription,
    NewHeader,
    ResponseDescription,
    validate,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory

_InnerT = TypeVar('_InnerT')


@final
class _CustomResponse(HttpResponse, Generic[_InnerT]):
    """We need to be sure that ``-> _CustomResponse[str]`` also works."""


class _CustomResponseController(Controller[PydanticSerializer]):
    @validate(ResponseDescription(return_type=str, status_code=HTTPStatus.OK))
    def get(self) -> _CustomResponse[str]:
        return _CustomResponse[str](b'"abc"')

    @validate(ResponseDescription(return_type=str, status_code=HTTPStatus.OK))
    def post(self) -> _CustomResponse[_InnerT]:  # pyright: ignore[reportInvalidTypeVarUse]
        return _CustomResponse[_InnerT](b'"abc"')


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
    ],
)
def test_validate_generic_response_subtype(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _CustomResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.content), str)


class _WrongHeadersController(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(return_type=list[str], status_code=HTTPStatus.OK),
    )
    def get(self) -> HttpResponse:
        """Has extra response headers."""
        return HttpResponse(b'[]', headers={'X-Custom': 'abc'})

    @validate(
        ResponseDescription(
            return_type=list[str],
            status_code=HTTPStatus.OK,
            headers={'X-Custom': HeaderDescription()},
        ),
    )
    def post(self) -> HttpResponse:
        """Has missing described headers."""
        return HttpResponse(b'[]')


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
    ],
)
def test_validate_wrong_headers(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response headers are validated."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WrongHeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert isinstance(json.loads(response.content)['detail'], str)


class _CorrectHeadersController(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(
            return_type=list[str],
            status_code=HTTPStatus.OK,
            headers={'X-Custom': HeaderDescription()},
        ),
    )
    def get(self) -> HttpResponse:
        """Has has matching response headers."""
        return HttpResponse(b'[]', headers={'X-Custom': 'abc'})

    @validate(
        ResponseDescription(
            return_type=list[str],
            status_code=HTTPStatus.OK,
            headers={'X-Custom': HeaderDescription(required=False)},
        ),
    )
    def post(self) -> HttpResponse:
        """Has optional header description."""
        return HttpResponse(b'[]')


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
    ],
)
def test_validate_correct_headers(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response headers are correct."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _CorrectHeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == []


class _MismatchingMetadata(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(int, status_code=HTTPStatus.OK),
    )
    def get(self) -> HttpResponse:
        return 1  # type: ignore[return-value]


def test_validate_over_regular_data(dmr_rf: DMRRequestFactory) -> None:
    """Ensures `@validate` can't mess metadata for raw requests."""
    request = dmr_rf.get('/whatever/')

    response = _MismatchingMetadata.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert '@modify' in json.loads(response.content)['detail']


def test_validate_required_for_responses() -> None:
    """Ensures `@validate` is required for `HttpResponse` returns."""
    with pytest.raises(EndpointMetadataError, match='@validate'):

        class _NoDecorator(Controller[PydanticSerializer]):
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_validate_on_non_response() -> None:
    """Ensures `@validate` can't be used on regular return types."""
    with pytest.raises(EndpointMetadataError, match='@validate'):

        class _WrongValidate(Controller[PydanticSerializer]):
            @validate(  # type: ignore[type-var]
                ResponseDescription(
                    return_type=str,
                    status_code=HTTPStatus.OK,
                ),
            )
            def get(self) -> str:
                raise NotImplementedError


def test_validate_duplicate_statuses() -> None:
    """Ensures `@validate` can't have duplicate status codes."""
    with pytest.raises(EndpointMetadataError, match='2 times'):

        class _DuplicateStatuses(Controller[PydanticSerializer]):
            @validate(
                ResponseDescription(int, status_code=HTTPStatus.OK),
                ResponseDescription(str, status_code=HTTPStatus.OK),
            )
            async def get(self) -> HttpResponse:
                raise NotImplementedError


def test_validate_raises_on_new_header() -> None:
    """Ensures `@validate` can't be used with `NewHeader`."""
    with pytest.raises(EndpointMetadataError, match='NewHeader'):

        class _WrongValidate(Controller[PydanticSerializer]):
            @validate(
                ResponseDescription(
                    return_type=str,
                    status_code=HTTPStatus.OK,
                    headers={'X-Test': NewHeader(value='Value')},  # type: ignore[dict-item]
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


class _EmptyResponseController(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(
            None,
            status_code=HTTPStatus.NO_CONTENT,
        ),
    )
    def get(self) -> HttpResponse:
        return self.to_response(
            None,
            status_code=HTTPStatus.NO_CONTENT,
        )


def test_validate_empty_response(dmr_rf: DMRRequestFactory) -> None:
    """Ensures `@validate` can validate empty response."""
    request = dmr_rf.get('/whatever/')

    response = _EmptyResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert json.loads(response.content) is None


class _TypedDictResponse(TypedDict):
    user: str


class _TypedDictResponseController(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(
            _TypedDictResponse,
            status_code=HTTPStatus.OK,
        ),
    )
    def get(self) -> HttpResponse:
        return self.to_response({'user': 'name'})

    @validate(
        ResponseDescription(
            _TypedDictResponse,
            status_code=HTTPStatus.CREATED,
        ),
    )
    def post(self) -> HttpResponse:
        return self.to_response({'user': 1})


def test_validate_type_dict_response(dmr_rf: DMRRequestFactory) -> None:
    """Ensures `@validate` can validate typed dicts."""
    request = dmr_rf.get('/whatever/')
    response = _TypedDictResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'user': 'name'}

    request = dmr_rf.post('/whatever/')
    response = _TypedDictResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'string_type',
                'loc': ['user'],
                'msg': 'Input should be a valid string',
                'input': 1,
            },
        ],
    })


class _LiteralResponseController(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(
            Literal[1],
            status_code=HTTPStatus.OK,
        ),
    )
    def get(self) -> HttpResponse:
        return self.to_response(1)

    @validate(
        ResponseDescription(
            Literal[1],
            status_code=HTTPStatus.CREATED,
        ),
    )
    def post(self) -> HttpResponse:
        return self.to_response(2)


def test_validate_literal_response(dmr_rf: DMRRequestFactory) -> None:
    """Ensures `@validate` can validate literals."""
    request = dmr_rf.get('/whatever/')
    response = _LiteralResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == 1

    request = dmr_rf.post('/whatever/')
    response = _LiteralResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'literal_error',
                'loc': [],
                'msg': 'Input should be 1',
                'input': 2,
                'ctx': {'expected': '1'},
            },
        ],
    })
