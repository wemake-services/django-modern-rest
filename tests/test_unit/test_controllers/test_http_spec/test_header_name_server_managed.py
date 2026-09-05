import re
from http import HTTPStatus
from typing import Final

import pydantic
import pytest
from django.http import HttpResponse

from dmr import Controller, HeaderSpec, ResponseSpec, validate
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import HttpSpec

_MATCH_PATTERN: Final = re.compile(
    r'Header .+ is not allowed in responses from endpoint .+',
)


class _BodyModel(pydantic.BaseModel):
    name: str


@pytest.mark.parametrize(
    'header',
    [
        'CONNECTION',
        'Keep-Alive',
        'Proxy-Authenticate',
        'Proxy-Authorization',
        'Te',
        'Trailer',
        'Transfer-Encoding',
        'Upgrade',
        'Date',
        'server',
    ],
)
def test_header_name_server_managed(
    header: str,
) -> None:
    """Ensure that responses must not have server managed headers."""
    header_spec = {header: HeaderSpec()}

    with pytest.raises(
        EndpointMetadataError,
        match=_MATCH_PATTERN,
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
