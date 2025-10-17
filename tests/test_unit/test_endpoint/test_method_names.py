from http import HTTPStatus
from typing import final

import pytest
from django.http import HttpResponse

from django_modern_rest import Controller, modify, validate
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


def test_modify_decorator_method_name(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that `modify` requires correct endpoint name."""
    with pytest.raises(ValueError, match='HTTPMethod'):

        class _WrongController(Controller[PydanticSerializer]):
            @modify(status_code=HTTPStatus.OK)
            def _get(self) -> list[int]:
                raise NotImplementedError


def test_verify_decorator_method_name(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that `modify` requires correct endpoint name."""
    with pytest.raises(ValueError, match='HTTPMethod'):

        class _WrongController(Controller[PydanticSerializer]):
            @validate(return_type=str, status_code=HTTPStatus.OK)
            def custom_name(self) -> HttpResponse:
                raise NotImplementedError


@final
class _NoEndpointsController(Controller[PydanticSerializer]):
    def regular_method(self) -> int:
        raise NotImplementedError

    def _get(self) -> int:
        raise NotImplementedError

    def __post(self) -> int:  # noqa: WPS112
        raise NotImplementedError


def test_controller_with_no_endpoints() -> None:
    """Ensures that only http method names are endpoints."""
    assert len(_NoEndpointsController.api_endpoints) == 0
