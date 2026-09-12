from typing import TypeVar

import pytest

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)


def test_base_controller_as_view() -> None:
    """Ensure that `Controller` itself cannot be used as a view."""
    with pytest.raises(EndpointMetadataError, match='is abstract'):
        Controller.as_view()


def test_generic_controller_as_view() -> None:
    """Ensure that controllers without an exact serializer are not views."""

    class _Custom(Controller[_SerializerT]):
        """Has a type var instead of a real serializer."""

        def get(self) -> str:
            raise NotImplementedError

    assert _Custom.is_abstract
    with pytest.raises(EndpointMetadataError, match='_Custom'):
        _Custom.as_view()


def test_controller_without_endpoints_as_view() -> None:
    """Ensure that controllers without any endpoints are not views."""

    class _Custom(Controller[PydanticSerializer]):
        """Has a real serializer, but nothing to serve."""

    assert _Custom.is_abstract
    with pytest.raises(EndpointMetadataError, match='_Custom'):
        _Custom.as_view()


def test_concrete_controller_as_view() -> None:
    """Ensure that regular controllers are still valid views."""

    class _Custom(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    assert not _Custom.is_abstract
    assert callable(_Custom.as_view())


def test_abstract_controller_in_router() -> None:
    """Ensure that abstract controllers cannot be added to a `Router`."""

    class _Custom(Controller[PydanticSerializer]):
        """Empty."""

    with pytest.raises(EndpointMetadataError, match='_Custom'):
        Router(urls=[path('custom/', _Custom.as_view())])
