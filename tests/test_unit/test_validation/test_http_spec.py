from http import HTTPStatus

import pytest

from django_modern_rest import Controller, modify
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@pytest.mark.parametrize(
    'status_code',
    [
        HTTPStatus.NO_CONTENT,
        HTTPStatus.NOT_MODIFIED,
    ],
)
def test_http_spec_none_body_for_status(
    dmr_rf: DMRRequestFactory,
    *,
    status_code: HTTPStatus,
) -> None:
    """Ensures body validation for some statuses work correctly."""
    with pytest.raises(EndpointMetadataError, match='`None`'):

        class _ValidController(Controller[PydanticSerializer]):
            @modify(status_code=status_code)
            def post(self) -> int:
                raise NotImplementedError
