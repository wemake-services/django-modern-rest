from typing import Generic

import pytest
from django.conf import LazySettings
from typing_extensions import TypedDict, TypeVar

from dmr import Body, Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.serializer import BaseSerializer


class _RequestModel(TypedDict):
    first_name: str


_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)
_RequestModelT = TypeVar('_RequestModelT', default=_RequestModel)


class _Reusable(
    Controller[_SerializerT],
    Generic[_SerializerT, _RequestModelT],
):
    """Reusable docstring."""

    def post(self, parsed_body: Body[_RequestModelT]) -> _RequestModelT:
        raise NotImplementedError


@pytest.fixture
def _project_serializer(settings: LazySettings) -> None:
    settings.DMR_SETTINGS = {'serializer': PydanticSerializer}


@pytest.mark.usefixtures('_project_serializer')
def test_as_view_uses_the_serializer_setting() -> None:
    """Ensures that a bare `as_view` falls back to the project serializer."""
    view = _Reusable.as_view()

    assert view.view_class.serializer is PydanticSerializer  # type: ignore[attr-defined]
    assert not view.view_class.is_abstract  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_project_serializer')
def test_as_view_argument_wins_over_setting() -> None:
    """Ensures that an explicit serializer beats the project one."""
    view = _Reusable.as_view(serializer=PydanticFastSerializer)

    assert view.view_class.serializer is PydanticFastSerializer  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_project_serializer')
def test_setting_does_not_touch_exact_serializers() -> None:
    """Ensures that controllers with their own serializer are left alone."""

    class _Concrete(Controller[PydanticFastSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    view = _Concrete.as_view()

    assert view.view_class.serializer is PydanticFastSerializer  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_project_serializer')
def test_setting_needs_endpoints_as_well() -> None:
    """Ensures that the setting does not make a view out of nothing."""

    class _NoEndpoints(Controller[_SerializerT]):
        """Has no endpoints to serve."""

    with pytest.raises(EndpointMetadataError, match='is abstract'):
        _NoEndpoints.as_view()


def test_no_serializer_setting_by_default() -> None:
    """Ensures that reusable controllers still need a serializer."""
    with pytest.raises(EndpointMetadataError, match='is abstract'):
        _Reusable.as_view()
