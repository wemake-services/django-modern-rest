from http import HTTPStatus
from typing import ClassVar

import pytest

from django_modern_rest import Controller, ResponseDescription
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer


def test_controller_either_sync_or_async() -> None:
    """Ensure that controllers can have either sync or async endpoints."""
    with pytest.raises(
        EndpointMetadataError,
        match='either be all sync or all async',
    ):

        class _MixedController(Controller[PydanticSerializer]):
            def get(self) -> str:
                raise NotImplementedError

            async def post(self) -> list[str]:
                raise NotImplementedError


def test_controller_duplicate_responses() -> None:
    """Ensure that controllers can't have duplicate status code."""
    with pytest.raises(
        EndpointMetadataError,
        match='403',
    ):

        class _MixedController(Controller[PydanticSerializer]):
            responses: ClassVar[list[ResponseDescription]] = [
                ResponseDescription(int, status_code=HTTPStatus.FORBIDDEN),
                ResponseDescription(str, status_code=HTTPStatus.FORBIDDEN),
            ]


def test_controller_http_spec() -> None:
    """Ensure that controllers with NO_CONTENT must not have bodies."""
    with pytest.raises(
        EndpointMetadataError,
        match='None',
    ):

        class _MixedController(Controller[PydanticSerializer]):
            responses: ClassVar[list[ResponseDescription]] = [
                ResponseDescription(int, status_code=HTTPStatus.NO_CONTENT),
            ]
