from __future__ import annotations

import sys
import types
from http import HTTPStatus
from typing import TYPE_CHECKING, TypeAlias, final

import pytest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST
from typing_extensions import Format, TypedDict

from dmr import Body, Controller
from dmr.decorators import endpoint_decorator
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.types import AnnotationsContext

if TYPE_CHECKING:
    from django.http import HttpResponse

    _TypeCheckOnlyAlias: TypeAlias = dict[str, int]


_RegularAlias: TypeAlias = list[int]


@final
class _Payload(TypedDict):
    token: str


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


def test_decorated_endpoint_annotations() -> None:
    """Ensure postponed annotations use the endpoint namespace."""

    class ExampleController:
        @endpoint_decorator(sensitive_post_parameters())
        def post(
            self,
            parsed_body: Body[_Payload],
        ) -> dict[str, str]:
            return {}

    annotations = AnnotationsContext()(ExampleController.post)

    assert annotations == {
        'parsed_body': Body[_Payload],
        'return': dict[str, str],
    }


def test_multiple_decorated_endpoint_annotations() -> None:
    """Ensure postponed annotations survive multiple endpoint decorators."""

    class ExampleController:
        @endpoint_decorator(csrf_exempt)
        @endpoint_decorator(require_POST)
        @endpoint_decorator(sensitive_post_parameters())
        def post(
            self,
            parsed_body: Body[_Payload],
        ) -> dict[str, str]:
            return {}

    annotations = AnnotationsContext()(ExampleController.post)

    assert annotations == {
        'parsed_body': Body[_Payload],
        'return': dict[str, str],
    }


@pytest.mark.skipif(sys.version_info < (3, 14), reason='format added in 3.14')
def test_annotation_inference_context314() -> None:  # pragma: no cover
    """Ensure that AnnotationsContext works correctly with format."""

    def some_function() -> 'Undefined': ...  # type: ignore[name-defined]  # noqa: F821, UP037

    assert AnnotationsContext(format=Format.STRING)(
        some_function,
    ) == {'return': "'Undefined'"}
