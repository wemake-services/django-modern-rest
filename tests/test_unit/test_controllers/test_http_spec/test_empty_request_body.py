from http import HTTPStatus
from typing import Final

import pydantic
import pytest
from django.http import HttpResponse

from dmr import Body, Controller, ResponseSpec, modify, validate
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import HttpSpec

_MATCH_PATTERN: Final = 'cannot have a request body'


class _BodyModel(pydantic.BaseModel):
    name: str


def test_empty_request_body_get_with_body() -> None:
    """Ensure that GET can use body parsing via endpoint args."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _Controller(Controller[PydanticSerializer]):
            def get(self, parsed_body: Body[_BodyModel]) -> str:
                raise NotImplementedError


def test_empty_request_body_head_with_body() -> None:
    """Ensure that HEAD can use body parsing via endpoint args."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _Controller(Controller[PydanticSerializer]):
            def head(self, parsed_body: Body[_BodyModel]) -> str:
                raise NotImplementedError


def test_empty_request_body_delete_with_body() -> None:
    """Ensure that DELETE can use body parsing via endpoint args."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _Controller(Controller[PydanticSerializer]):
            def delete(self, parsed_body: Body[_BodyModel]) -> str:
                raise NotImplementedError


def test_empty_request_body_connect_with_body() -> None:
    """Ensure that CONNECT can use body parsing via endpoint args."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _Controller(Controller[PydanticSerializer]):
            def connect(self, parsed_body: Body[_BodyModel]) -> str:
                raise NotImplementedError


def test_empty_request_body_trace_with_body() -> None:
    """Ensure that TRACE can use body parsing via endpoint args."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _Controller(Controller[PydanticSerializer]):
            def trace(self, parsed_body: Body[_BodyModel]) -> str:
                raise NotImplementedError


def test_empty_request_body_post_with_body_works() -> None:
    """Ensure that POST with Body works fine."""

    class _GoodController(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[_BodyModel]) -> str:
            raise NotImplementedError

    assert 'POST' in _GoodController.api_endpoints


def test_empty_request_body_put_with_body_works() -> None:
    """Ensure that PUT with Body works fine."""

    class _GoodController(Controller[PydanticSerializer]):
        def put(self, parsed_body: Body[_BodyModel]) -> str:
            raise NotImplementedError

    assert 'PUT' in _GoodController.api_endpoints


def test_empty_request_body_patch_with_body_works() -> None:
    """Ensure that PATCH with Body works fine."""

    class _GoodController(Controller[PydanticSerializer]):
        def patch(self, parsed_body: Body[_BodyModel]) -> str:
            raise NotImplementedError

    assert 'PATCH' in _GoodController.api_endpoints


def test_empty_request_body_disabled_controller() -> None:
    """Ensure that validation can be disabled on controller level."""

    class _Controller(Controller[PydanticSerializer]):
        no_validate_http_spec = {HttpSpec.empty_request_body}

        def get(self, parsed_body: Body[_BodyModel]) -> str:
            raise NotImplementedError

    assert 'GET' in _Controller.api_endpoints


def test_empty_request_body_disabled_scope() -> None:
    """Ensure that disabling on one controller does not affect others."""

    class _Controller(Controller[PydanticSerializer]):
        no_validate_http_spec = {HttpSpec.empty_request_body}

        def get(self, parsed_body: Body[_BodyModel]) -> str:
            raise NotImplementedError

    assert 'GET' in _Controller.api_endpoints

    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _AnotherController(Controller[PydanticSerializer]):
            def get(self, parsed_body: Body[_BodyModel]) -> str:
                raise NotImplementedError


def test_empty_request_body_disabled_on_modify() -> None:
    """Ensure validation can be disabled on endpoint level with @modify."""

    class _Controller(Controller[PydanticSerializer]):
        @modify(no_validate_http_spec={HttpSpec.empty_request_body})
        def get(self, parsed_body: Body[_BodyModel]) -> str:
            raise NotImplementedError

    assert 'GET' in _Controller.api_endpoints


def test_empty_request_body_disabled_on_validate() -> None:
    """Ensure validation can be disabled on endpoint level with @validate."""

    class _Controller(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            no_validate_http_spec={HttpSpec.empty_request_body},
        )
        def get(self, parsed_body: Body[_BodyModel]) -> HttpResponse:
            raise NotImplementedError

    assert 'GET' in _Controller.api_endpoints


def test_empty_request_body_no_body_method_works() -> None:
    """Ensure that GET without Body component works fine."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    assert 'GET' in _Controller.api_endpoints
