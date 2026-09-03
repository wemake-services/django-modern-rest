from collections.abc import Mapping
from http import HTTPStatus
from typing import Final

import pydantic
import pytest
from django.http import HttpResponse

from dmr import Controller, HeaderSpec, ResponseSpec, validate
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import HttpSpec

_MATCH_PATTER: Final[str] = (
    r'Header .+ is not allowed '
    r'in responses from endpoint .+'
)


class _BodyModel(pydantic.BaseModel):
    name: str


@pytest.mark.parametrize(
    'header',
    [
        'Connection',
        'Keep-Alive',
        'Proxy-Authenticate',
        'Proxy-Authorization',
        'Te',
        'Trailer',
        'Transfer-Encoding',
        'Upgrade',
        'Content-Length',
        'Date',
        'Server',
    ],
)
def test_header_name_server_managed(
    header: str,
) -> None:
    """Ensure that responses must not have server managed headers."""
    header_spec = {header: HeaderSpec()}

    with pytest.raises(
        EndpointMetadataError,
        match=_MATCH_PATTER,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    status_code=HTTPStatus.OK,
                    headers=header_spec,
                    return_type=None,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


@pytest.mark.parametrize(
    'header',
    [{'CONNECTION': HeaderSpec()}, {'Content-LENGTH': HeaderSpec()}],
)
def test_header_name_server_managed_casing(
    header: Mapping[str, HeaderSpec],
) -> None:
    """Ensure that validation is case-insensitive."""
    with pytest.raises(
        EndpointMetadataError,
        match=_MATCH_PATTER,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    status_code=HTTPStatus.OK,
                    headers=header,
                    return_type=None,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_header_name_server_managed_controller() -> None:
    """Ensure that the validation can be disabled on controller level."""
    header = {'Content-Length': HeaderSpec()}

    class _Mixed(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                status_code=HTTPStatus.OK,
                headers=header,
                return_type=None,
            ),
            no_validate_http_spec={HttpSpec.header_name_server_managed},
        )
        def get(self) -> HttpResponse:
            raise NotImplementedError


def test_server_managed_header_controller_scoped() -> None:
    """Ensure that disabling on one controller does not affect other."""
    header = {'Keep-Alive': HeaderSpec()}

    class GoodController(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                status_code=HTTPStatus.OK,
                headers=header,
                return_type=None,
            ),
            no_validate_http_spec={HttpSpec.header_name_server_managed},
        )
        def get(self) -> HttpResponse:
            raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match=_MATCH_PATTER,
    ):

        class BadController(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    status_code=HTTPStatus.OK,
                    headers=header,
                    return_type=None,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_server_managed_header_skip_validation() -> None:
    """Ensure skip_validation allows server-managed response headers."""
    header = {'Proxy-Authorization': HeaderSpec(skip_validation=True)}

    class _Mixed(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                status_code=HTTPStatus.OK,
                headers=header,
                return_type=None,
            ),
        )
        def get(self) -> HttpResponse:
            raise NotImplementedError


def test_server_managed_header_with_other_headers() -> None:
    """Ensure that other headers don't raise EndpointMetadataError."""
    header = {'X-API-TOKEN': HeaderSpec(), 'csrf-token': HeaderSpec()}

    class _Mixed(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                status_code=HTTPStatus.OK,
                headers=header,
                return_type=None,
            ),
        )
        def get(self) -> HttpResponse:
            raise NotImplementedError
