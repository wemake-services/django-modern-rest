from http import HTTPStatus

import pydantic
import pytest
from django.http import HttpResponse

from dmr import (
    Blueprint,
    Body,
    Controller,
    ResponseSpec,
    modify,
    validate,
)
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import HttpSpec

_MATCH_PATTERN = 'cannot have a request body'


class _BodyModel(pydantic.BaseModel):
    name: str


def test_empty_request_body_get_with_body() -> None:
    """Ensure that GET with Body raises error."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _BadController(Controller[PydanticSerializer], Body[_BodyModel]):
            def get(self) -> str:
                raise NotImplementedError


def test_empty_request_body_head_with_body() -> None:
    """Ensure that HEAD with Body raises error."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _BadController(Controller[PydanticSerializer], Body[_BodyModel]):
            def head(self) -> str:
                raise NotImplementedError


def test_empty_request_body_delete_with_body() -> None:
    """Ensure that DELETE with Body raises error."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _BadController(Controller[PydanticSerializer], Body[_BodyModel]):
            def delete(self) -> str:
                raise NotImplementedError


def test_empty_request_body_connect_with_body() -> None:
    """Ensure that CONNECT with Body raises error."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _BadController(Controller[PydanticSerializer], Body[_BodyModel]):
            def connect(self) -> str:
                raise NotImplementedError


def test_empty_request_body_trace_with_body() -> None:
    """Ensure that TRACE with Body raises error."""
    with pytest.raises(EndpointMetadataError, match=_MATCH_PATTERN):

        class _BadController(Controller[PydanticSerializer], Body[_BodyModel]):
            def trace(self) -> str:
                raise NotImplementedError


def test_empty_request_body_post_with_body_works() -> None:
    """Ensure that POST with Body works fine."""

    class _GoodController(Controller[PydanticSerializer], Body[_BodyModel]):
        def post(self) -> str:
            raise NotImplementedError

    assert 'POST' in _GoodController.api_endpoints


def test_empty_request_body_put_with_body_works() -> None:
    """Ensure that PUT with Body works fine."""

    class _GoodController(Controller[PydanticSerializer], Body[_BodyModel]):
        def put(self) -> str:
            raise NotImplementedError

    assert 'PUT' in _GoodController.api_endpoints


def test_empty_request_body_patch_with_body_works() -> None:
    """Ensure that PATCH with Body works fine."""

    class _GoodController(Controller[PydanticSerializer], Body[_BodyModel]):
        def patch(self) -> str:
            raise NotImplementedError

    assert 'PATCH' in _GoodController.api_endpoints


def test_empty_request_body_disabled_controller() -> None:
    """Ensure that validation can be disabled on controller level."""

    class _Controller(Controller[PydanticSerializer], Body[_BodyModel]):
        no_validate_http_spec = {HttpSpec.empty_request_body}

        def get(self) -> str:
            raise NotImplementedError

    assert 'GET' in _Controller.api_endpoints


def test_empty_request_body_disabled_on_blueprint() -> None:
    """Ensure that validation can be disabled on blueprint level."""

    class _Blueprint(Blueprint[PydanticSerializer], Body[_BodyModel]):
        no_validate_http_spec = {HttpSpec.empty_request_body}

        def get(self) -> str:
            raise NotImplementedError

    class _Controller(Controller[PydanticSerializer]):
        blueprints = [_Blueprint]

    assert 'GET' in _Controller.api_endpoints


def test_empty_request_body_disabled_on_modify() -> None:
    """Ensure validation can be disabled on endpoint level with @modify."""

    class _Controller(Controller[PydanticSerializer], Body[_BodyModel]):
        @modify(no_validate_http_spec={HttpSpec.empty_request_body})
        def get(self) -> str:
            raise NotImplementedError

    assert 'GET' in _Controller.api_endpoints


def test_empty_request_body_disabled_on_validate() -> None:
    """Ensure validation can be disabled on endpoint level with @validate."""

    class _Controller(Controller[PydanticSerializer], Body[_BodyModel]):
        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            no_validate_http_spec={HttpSpec.empty_request_body},
        )
        def get(self) -> HttpResponse:
            raise NotImplementedError

    assert 'GET' in _Controller.api_endpoints


def test_empty_request_body_no_body_method_works() -> None:
    """Ensure that GET without Body component works fine."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    assert 'GET' in _Controller.api_endpoints
