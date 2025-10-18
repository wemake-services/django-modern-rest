from http import HTTPStatus
from typing import ClassVar

import pytest

from django_modern_rest import (
    Controller,
    ResponseDescription,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


def test_controller_duplicate_responses(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures validation can validate api errors on controllers."""
    with pytest.raises(EndpointMetadataError, match='402'):

        class _Wrong(Controller[PydanticSerializer]):
            responses: ClassVar[list[ResponseDescription]] = [
                ResponseDescription(
                    int,
                    status_code=HTTPStatus.PAYMENT_REQUIRED,
                ),
                ResponseDescription(
                    str,
                    status_code=HTTPStatus.PAYMENT_REQUIRED,
                ),
            ]
