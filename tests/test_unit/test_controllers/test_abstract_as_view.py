from typing import TypeVar

import pytest

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
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


def test_explicitly_abstract_controller_as_view() -> None:
    """Ensure that explicit `is_abstract = True` is respected."""

    class _Custom(Controller[PydanticSerializer]):
        is_abstract = True

        def get(self) -> str:
            raise NotImplementedError

    assert _Custom.is_abstract
    # It still has a real endpoint, it is just not routed:
    assert _Custom.api_endpoints
    with pytest.raises(EndpointMetadataError, match='_Custom'):
        _Custom.as_view()


def test_child_of_abstract_controller_is_concrete() -> None:
    """Ensure that subclasses of abstract controllers become concrete."""

    class _Custom(Controller[PydanticSerializer]):
        is_abstract = True

        def get(self) -> str:
            raise NotImplementedError

    class _Concrete(_Custom):
        """Nothing is defined here on purpose."""

    assert not _Concrete.is_abstract
    assert callable(_Concrete.as_view())


def test_child_can_declare_itself_abstract() -> None:
    """Ensure that subclasses can also declare themselves abstract."""

    class _Custom(Controller[PydanticSerializer]):
        is_abstract = True

        def get(self) -> str:
            raise NotImplementedError

    class _StillAbstract(_Custom):
        is_abstract = True

    assert _StillAbstract.is_abstract
    with pytest.raises(EndpointMetadataError, match='_StillAbstract'):
        _StillAbstract.as_view()
