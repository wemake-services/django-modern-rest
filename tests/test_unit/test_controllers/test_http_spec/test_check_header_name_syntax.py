import re
from http import HTTPStatus
from typing import Final

import pydantic
import pytest
from django.http import HttpResponse

from dmr import (
    Controller,
    HeaderSpec,
    NewHeader,
    ResponseSpec,
    modify,
    validate,
)
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import HttpSpec

_MATCH_PATTERN: Final = re.compile(
    r'Header .+ is not following http spec.',
)


class _UserModel(pydantic.BaseModel):
    email: str


@pytest.mark.parametrize(
    'header',
    ['X Custom Header', '@@@'],
)
def test_check_header_name_syntax(
    header: str,
) -> None:
    """Ensure that response headers' names follow http spec syntax."""
    headers = {header: HeaderSpec()}

    with pytest.raises(
        EndpointMetadataError,
        match=_MATCH_PATTERN,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    status_code=HTTPStatus.OK,
                    headers=headers,
                    return_type=None,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


@pytest.mark.parametrize(
    'header',
    ['X Custom Header', '@@@'],
)
def test_check_new_header_name_syntax(
    header: str,
) -> None:
    """Ensure that new headers' names follow http spec syntax."""
    with pytest.raises(
        EndpointMetadataError,
        match=_MATCH_PATTERN,
    ):

        class _Mixed(Controller[PydanticSerializer]):
            @modify(
                headers={header: NewHeader(value='1')},
            )
            def get(self) -> _UserModel:
                raise NotImplementedError


def test_check_header_name_syntax_controller() -> None:
    """Ensure that the validation can be disabled on controller level."""

    class _Mixed(Controller[PydanticSerializer]):
        @modify(
            headers={'X Custom Header': NewHeader(value='1')},
            no_validate_http_spec={HttpSpec.header_name_syntax},
        )
        def get(self) -> _UserModel:
            raise NotImplementedError
