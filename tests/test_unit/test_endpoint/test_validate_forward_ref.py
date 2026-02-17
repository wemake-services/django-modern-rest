from __future__ import annotations  # <- required for test

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from dmr import (
    Controller,
    ResponseSpec,
    validate,
)
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory

if TYPE_CHECKING:
    from django.http import HttpResponse  # <- required for test


def test_validate_forward_ref(dmr_rf: DMRRequestFactory) -> None:
    """Ensures `@validate` cannot work on forward ref annotation."""
    with pytest.raises(UnsolvableAnnotationsError, match=r'\.get'):

        class _CorrectHeadersController(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    return_type=list[str],
                    status_code=HTTPStatus.OK,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError
