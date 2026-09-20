from typing import ClassVar, Generic

import pytest
from typing_extensions import TypedDict, TypeVar

from dmr import Body, Controller
from dmr.exceptions import EndpointMetadataError, UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.serializer import BaseSerializer


class _RequestModel(TypedDict):
    first_name: str


_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)
_RequestModelT = TypeVar('_RequestModelT', default=_RequestModel)
_NoDefaultT = TypeVar('_NoDefaultT')


class _Reusable(
    Controller[_SerializerT],
    Generic[_SerializerT, _RequestModelT],
):
    """Reusable docstring."""

    #: Required field that a subclass would normally fill in.
    required_field: ClassVar[str]

    def post(self, parsed_body: Body[_RequestModelT]) -> _RequestModelT:
        raise NotImplementedError


class _Unresolved(
    Controller[_SerializerT],
    Generic[_SerializerT, _NoDefaultT],
):
    """Has a type var that no default can fill in."""

    def post(self, parsed_body: Body[_NoDefaultT]) -> None:
        raise NotImplementedError


def test_reusable_as_view_with_serializer() -> None:
    """Ensures that a serializer makes a reusable controller routable."""
    view = _Reusable.as_view(serializer=PydanticSerializer)

    assert callable(view)
    assert view.view_class.serializer is PydanticSerializer  # type: ignore[attr-defined]
    assert not view.view_class.is_abstract  # type: ignore[attr-defined]
    assert view.view_class.api_endpoints.keys() == {'POST'}  # type: ignore[attr-defined]


def test_as_view_fills_in_required_fields() -> None:
    """Ensures that any declared attribute can be passed."""
    view = _Reusable.as_view(
        serializer=PydanticSerializer,
        required_field='filled in',
        validate_responses=False,
    )

    assert view.view_class.required_field == 'filled in'  # type: ignore[attr-defined]
    assert view.view_class.validate_responses is False  # type: ignore[attr-defined]


def test_as_view_class_attrs_keep_identity() -> None:
    """Ensures that the built subclass looks like the controller it copies."""
    view_class = _Reusable.as_view(serializer=PydanticSerializer).view_class  # type: ignore[attr-defined]

    assert view_class.__name__ == _Reusable.__name__
    assert view_class.__qualname__ == _Reusable.__qualname__
    assert view_class.__module__ == _Reusable.__module__
    assert view_class.__doc__ == _Reusable.__doc__
    assert issubclass(view_class, _Reusable)


def test_as_view_class_attrs_keep_base() -> None:
    """Ensures that routing a reusable controller does not mutate it."""
    _Reusable.as_view(serializer=PydanticSerializer, required_field='one')

    assert _Reusable.is_abstract
    assert getattr(_Reusable, 'serializer', None) is None
    assert getattr(_Reusable, 'required_field', None) is None


def test_as_view_with_different_serializers() -> None:
    """Ensures that one reusable controller serves several serializers."""
    regular_view = _Reusable.as_view(serializer=PydanticSerializer)
    fast_view = _Reusable.as_view(serializer=PydanticFastSerializer)

    assert regular_view.view_class.serializer is PydanticSerializer  # type: ignore[attr-defined]
    assert fast_view.view_class.serializer is PydanticFastSerializer  # type: ignore[attr-defined]
    assert regular_view.view_class is not fast_view.view_class  # type: ignore[attr-defined]


def test_as_view_class_attrs_on_concrete() -> None:
    """Ensures that a concrete controller still takes other attributes."""

    class _Concrete(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    view = _Concrete.as_view(validate_responses=False)

    assert view.view_class.validate_responses is False  # type: ignore[attr-defined]


def test_as_view_serializer_on_concrete() -> None:
    """Ensures that overriding an exact serializer is rejected."""

    class _Concrete(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(EndpointMetadataError, match='already has'):
        _Concrete.as_view(serializer=PydanticFastSerializer)


def test_as_view_unknown_class_attr() -> None:
    """Ensures that a name the controller never declares is rejected."""
    with pytest.raises(EndpointMetadataError, match='does not declare'):
        _Reusable.as_view(serializer=PydanticSerializer, requird_field='typo')


def test_as_view_http_method_class_attr() -> None:
    """Ensures that http methods cannot be replaced this way."""
    with pytest.raises(EndpointMetadataError, match='http method name'):
        _Reusable.as_view(serializer=PydanticSerializer, post=None)


def test_as_view_abstract_error_hint() -> None:
    """Ensures that the abstract error points at the new arguments."""
    with pytest.raises(EndpointMetadataError, match='missing'):
        _Reusable.as_view()


def test_as_view_class_attrs_without_endpoints() -> None:
    """Ensures that a serializer alone does not make a view out of nothing."""

    class _NoEndpoints(Controller[_SerializerT]):
        """Has no endpoints to serve."""

    with pytest.raises(EndpointMetadataError, match='is abstract'):
        _NoEndpoints.as_view(serializer=PydanticSerializer)


def test_as_view_class_attrs_unresolved_type_var() -> None:
    """Ensures that type vars without defaults are still required."""
    with pytest.raises(UnsolvableAnnotationsError, match='_NoDefaultT'):
        _Unresolved.as_view(serializer=PydanticSerializer)
