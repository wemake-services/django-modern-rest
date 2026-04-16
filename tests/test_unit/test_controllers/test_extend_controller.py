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

    assert _Custom.is_abstract
    assert getattr(_Custom, 'api_endpoints', None) is None
    assert getattr(_Custom, 'serializer', None) is None

    class _Intermediate(_Custom[PydanticSerializer]):
        """Also empty, but not generic."""

    assert _Intermediate.is_abstract
    assert _Intermediate.serializer is PydanticSerializer
    assert _Intermediate.api_endpoints == {}

    class _Final(_Intermediate):
        """Final controller with endpoints."""

        def get(self) -> str:
            raise NotImplementedError

    assert not _Final.is_abstract
    assert _Final.serializer is PydanticSerializer
    assert _Final.api_endpoints.keys() == {'GET'}


def test_controller_wrong_serializer() -> None:
    """Ensure that we must pass BaseSerializer types to controllers."""
    with pytest.raises(UnsolvableAnnotationsError, match='BaseSerializer'):

        class _Custom(Controller[int]):  # type: ignore[type-var]
            """Empty."""


def test_controller_empty() -> None:
    """Ensure that we can create empty controllers."""

    class _Custom(Controller[PydanticSerializer]):
        """Empty."""


def test_controller_base_serializer() -> None:
    """Ensure that we can't create controllers with BaseSerizliser itself."""
    with pytest.raises(UnsolvableAnnotationsError, match='BaseSerializer'):

        class _Custom(Controller[BaseSerializer]):
            """Empty."""
