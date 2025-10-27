from __future__ import annotations  # <- required for test

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from django_modern_rest import (
    Controller,
    ResponseDescription,
    validate,
)
from django_modern_rest.exceptions import UnsolvableAnnotationsError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory

if TYPE_CHECKING:
    from django.http import HttpResponse  # <- required for test


def test_validate_forward_ref(dmr_rf: DMRRequestFactory) -> None:
    """Ensures `@validate` cannot work on forward ref annotation."""
    with pytest.raises(UnsolvableAnnotationsError, match=r'\.get'):

        class _CorrectHeadersController(Controller[PydanticSerializer]):
            @validate(
                ResponseDescription(
                    return_type=list[str],
                    status_code=HTTPStatus.OK,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError
