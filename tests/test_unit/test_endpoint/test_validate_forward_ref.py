from __future__ import annotations  # <- required for test

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from dmr import Controller, ResponseSpec, validate
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory
from dmr.types import AnnotationsContext

if TYPE_CHECKING:
    from django.http import HttpResponse  # <- required for test


def test_validate_forward_ref(dmr_rf: DMRRequestFactory) -> None:
    """Ensures `@validate` cannot work on forward ref annotation."""
    with pytest.raises(UnsolvableAnnotationsError, match=r'\.get'):

        class _WrongHeadersController(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(
                    return_type=list[str],
                    status_code=HTTPStatus.OK,
                ),
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_validate_forward_ref_custom(dmr_rf: DMRRequestFactory) -> None:
    """Ensures custom context helps to solve annotations."""
    from django.http import HttpResponse as _HttpResponse  # noqa: PLC0415

    assert 'HttpResponse' not in globals()  # noqa: WPS421
    assert 'HttpResponse' not in locals()  # noqa: WPS421

    class _CorrectHeadersController(Controller[PydanticSerializer]):
        annotations_context = AnnotationsContext(
            globalns={'HttpResponse': _HttpResponse},
        )

        @validate(
            ResponseSpec(
                return_type=list[str],
                status_code=HTTPStatus.OK,
            ),
        )
        def get(self) -> HttpResponse:
            raise NotImplementedError
