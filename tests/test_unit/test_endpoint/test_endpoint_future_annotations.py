from __future__ import annotations

import sys
import types
from http import HTTPStatus
from typing import TYPE_CHECKING, TypeAlias

import pytest
from typing_extensions import Format

from dmr import Controller
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.types import AnnotationsContext

if TYPE_CHECKING:
    from django.http import HttpResponse

    _TypeCheckOnlyAlias: TypeAlias = dict[str, int]


_RegularAlias: TypeAlias = list[int]


def test_unsolvable_annotations() -> None:
    """Ensure that we fail early when some annotations can't be solved."""
    with pytest.raises(UnsolvableAnnotationsError, match='get'):

        class _Wrong(Controller[PydanticSerializer]):
            def get(self) -> _TypeCheckOnlyAlias:
                raise NotImplementedError


def test_unsolvable_response_annotations() -> None:
    """Ensure that we fail early when some annotations can't be solved."""
    with pytest.raises(UnsolvableAnnotationsError, match='get'):

        class _Wrong(Controller[PydanticSerializer]):
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_solvable_response_annotations() -> None:
    """Ensure that string annotations still can be solved."""

    class MyController(Controller[PydanticSerializer]):
        def get(self) -> _RegularAlias:
            raise NotImplementedError

    metadata = MyController.api_endpoints['GET'].metadata
    assert metadata.responses[HTTPStatus.OK].return_type == _RegularAlias


def test_annotation_inference_context() -> None:
    """Ensure that AnnotationsContext works correctly."""
    assert AnnotationsContext()(
        test_solvable_response_annotations,
    ) == {'return': types.NoneType}

    def some_function() -> 'Undefined': ...  # type: ignore[name-defined]  # noqa: F821, UP037

    with pytest.raises(UnsolvableAnnotationsError, match='cannot be solved'):
        AnnotationsContext()(some_function)

    assert AnnotationsContext(globalns={'Undefined': int})(
        some_function,
    ) == {'return': int}


@pytest.mark.skipif(sys.version_info < (3, 14), reason='format added in 3.14')
def test_annotation_inference_context314() -> None:  # pragma: no cover
    """Ensure that AnnotationsContext works correctly with format."""

    def some_function() -> 'Undefined': ...  # type: ignore[name-defined]  # noqa: F821, UP037

    assert AnnotationsContext(format=Format.STRING)(
        some_function,
    ) == {'return': "'Undefined'"}
