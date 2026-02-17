from typing import TypeVar

import pytest

from dmr import Controller
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)


def test_controller_without_serializer() -> None:
    """Ensure that we need at least one type param for component."""
    with pytest.raises(UnsolvableAnnotationsError, match='_Custom'):

        class _Custom(Controller):  # type: ignore[type-arg]
            """Empty."""


def test_controller_generic_subclass() -> None:
    """Ensure that we can extend controllers with generics."""

    class _Custom(Controller[_SerializerT]):
        """Empty."""

    assert getattr(_Custom, 'api_endpoints', None) is None
    assert getattr(_Custom, 'serializer', None) is None
    assert getattr(_Custom, '_existing_http_methods', None) is None

    class _Final(_Custom[PydanticSerializer]):
        """Also empty, but not generic."""

    assert _Final.serializer is PydanticSerializer
    assert _Final.api_endpoints == {}
    assert _Final._existing_http_methods == {}


def test_controller_wrong_serializer() -> None:
    """Ensure that we must pass BaseSerializer types to controllers."""
    with pytest.raises(UnsolvableAnnotationsError, match='BaseSerializer'):

        class _Custom(Controller[int]):  # type: ignore[type-var]
            """Empty."""


def test_controller_empty() -> None:
    """Ensure that we can create empty controllers."""

    class _Custom(Controller[PydanticSerializer]):
        """Empty."""
