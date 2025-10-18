from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from inline_snapshot import snapshot

if TYPE_CHECKING:
    from django.http import HttpResponse

    _TypeCheckOnlyAlias: TypeAlias = dict[str, int]


import pytest

from django_modern_rest import Controller
from django_modern_rest.exceptions import UnsolvableAnnotationsError
from django_modern_rest.plugins.pydantic import PydanticSerializer

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

    endpoint = MyController.api_endpoints['get']
    assert str(endpoint.response_validator.metadata.responses) == snapshot(
        '{<HTTPStatus.OK: 200>: '
        'ResponseDescription(return_type=list[int], '
        'status_code=<HTTPStatus.OK: 200>, headers=Empty())}',
    )
