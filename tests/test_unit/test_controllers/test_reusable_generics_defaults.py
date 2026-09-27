import sys
import textwrap
from http import HTTPStatus
from typing import Any, Generic

import pydantic
import pytest
from django.http import HttpResponse
from typing_extensions import TypeVar

from dmr import Body, Controller, Query, ResponseSpec, validate
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.types import safe_typevar


class _DefaultModel(pydantic.BaseModel):
    user: str


class _ExactModel(pydantic.BaseModel):
    other: str


_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
    default=PydanticSerializer,
)
_ModelT = TypeVar('_ModelT', default=_DefaultModel)
#: `PEP 696` allows defaults to be other type vars.
_LinkedT = TypeVar('_LinkedT', default=_ModelT)
#: Regular type var without any default.
_AnySerializerT = TypeVar('_AnySerializerT', bound=BaseSerializer)


class _BaseController(
    Controller[_SerializerT],
    Generic[_SerializerT, _ModelT],
):
    """Both the serializer and the request model have defaults."""

    def post(self, parsed_body: Body[_ModelT]) -> str:
        raise NotImplementedError


def _body_models(
    controller: type[Controller[Any]],
) -> list[Any]:
    metadata = controller.api_endpoints['POST'].metadata
    return [parser[1] for parser in metadata.component_parsers]


def test_reusable_controller_is_still_abstract() -> None:
    """Ensure that defaults don't make the declaring controller concrete."""
    assert _BaseController.is_abstract
    assert getattr(_BaseController, 'serializer', None) is None
    assert getattr(_BaseController, 'api_endpoints', None) is None


def test_defaults_for_bare_subclass() -> None:
    """Ensure that a subclass without type args uses all the defaults."""

    class BareController(_BaseController):
        """Both type vars fall back to their defaults."""

    assert not BareController.is_abstract
    assert BareController.serializer is PydanticSerializer
    assert _body_models(BareController) == [_DefaultModel]


def test_defaults_for_partial_type_args() -> None:
    """Ensure that missing type args fall back to their defaults."""

    class PartialController(_BaseController[PydanticSerializer]):
        """Only the serializer is given, the model is defaulted."""

    assert not PartialController.is_abstract
    assert PartialController.serializer is PydanticSerializer
    assert _body_models(PartialController) == [_DefaultModel]


def test_exact_type_args_win_over_defaults() -> None:
    """Ensure that defaults are only used when type args are missing."""

    class ExactController(_BaseController[PydanticSerializer, _ExactModel]):
        """Both type args are given."""

    assert not ExactController.is_abstract
    assert _body_models(ExactController) == [_ExactModel]


def test_defaults_in_several_layers() -> None:
    """Ensure that defaults are resolved through the whole inheritance."""

    class _ReusableController(
        _BaseController[_SerializerT, _ModelT],
        Generic[_SerializerT, _ModelT],
    ):
        """Some framework can provide such a type."""

    class FinalController(_ReusableController):
        """Nothing is given on any of the levels."""

    assert _ReusableController.is_abstract
    assert not FinalController.is_abstract
    assert FinalController.serializer is PydanticSerializer
    assert _body_models(FinalController) == [_DefaultModel]


def test_defaults_in_async_controller() -> None:
    """Ensure that async controllers resolve defaults the same way."""

    class _AsyncController(
        Controller[_SerializerT],
        Generic[_SerializerT, _ModelT],
    ):
        async def post(self, parsed_body: Body[_ModelT]) -> str:
            raise NotImplementedError

    class BareController(_AsyncController):
        """Nothing is given."""

    assert not BareController.is_abstract
    assert BareController.is_async
    assert BareController.serializer is PydanticSerializer
    assert _body_models(BareController) == [_DefaultModel]


def test_default_pointing_to_other_type_var() -> None:
    """Ensure that a type var default can be another type var."""

    class _LinkedController(
        Controller[_SerializerT],
        Generic[_SerializerT, _ModelT, _LinkedT],
    ):
        """``_LinkedT`` defaults to whatever ``_ModelT`` is."""

        def post(
            self,
            parsed_body: Body[_ModelT],
            parsed_query: Query[_LinkedT],
        ) -> str:
            raise NotImplementedError

    class ExactController(_LinkedController[PydanticSerializer, _ExactModel]):
        """``_LinkedT`` must become ``_ExactModel`` as well."""

    class BareController(_LinkedController):
        """``_LinkedT`` must become ``_DefaultModel`` via ``_ModelT``."""

    assert _body_models(ExactController) == [_ExactModel, _ExactModel]
    assert _body_models(BareController) == [_DefaultModel, _DefaultModel]
    assert BareController.serializer is PydanticSerializer


def test_defaults_in_validate() -> None:
    """Ensure that ``@validate`` works with type var defaults."""

    class _ValidateController(
        Controller[_SerializerT],
        Generic[_SerializerT, _ModelT],
    ):
        @validate(
            ResponseSpec(
                safe_typevar('_ModelT', stacklevel=2),
                status_code=HTTPStatus.OK,
            ),
        )
        def post(self) -> HttpResponse:
            raise NotImplementedError

    class BareController(_ValidateController):
        """Nothing is given."""

    responses = BareController.api_endpoints['POST'].metadata.responses
    assert responses[HTTPStatus.OK].return_type is _DefaultModel


def test_still_generic_controller_uses_defaults() -> None:
    """Ensure that explicitly passed type vars are resolved to defaults."""

    class StillGenericController(
        _BaseController[PydanticSerializer, _ModelT],
    ):
        """It is still generic, but it can be routed with the default."""

    class ExactController(StillGenericController[_ExactModel]):
        """And it can still be subclassed with an exact model."""

    assert _body_models(StillGenericController) == [_DefaultModel]
    assert _body_models(ExactController) == [_ExactModel]


def test_type_var_without_default() -> None:
    """Ensure that type vars without defaults are still required."""

    class _MixedController(
        Controller[_AnySerializerT],
        Generic[_AnySerializerT, _ModelT],
    ):
        """Only the request model has a default."""

        def post(self, parsed_body: Body[_ModelT]) -> str:
            raise NotImplementedError

    class BareController(_MixedController):  # type: ignore[type-arg]
        """The serializer has no default, so this one stays abstract."""

    class FinalController(_MixedController[PydanticSerializer]):
        """But the model still falls back to its default."""

    assert BareController.is_abstract
    assert getattr(BareController, 'serializer', None) is None
    assert not FinalController.is_abstract
    assert _body_models(FinalController) == [_DefaultModel]


@pytest.mark.skipif(
    sys.version_info < (3, 13),
    reason='PEP-696 syntax was added in 3.13',
)
def test_pep696_type_params() -> None:  # pragma: >=3.13 cover
    """Ensure that native type var defaults are supported on 3.13+."""
    # We have to use `exec` here, because 3.13+ syntax
    # will cause `SyntaxError` for the whole test module.
    ns = globals().copy()  # noqa: WPS421
    exec(  # noqa: S102, WPS421
        textwrap.dedent(
            """
            class NativeController[
                _SerT: BaseSerializer = PydanticSerializer,
                _ModT = _DefaultModel,
            ](Controller[_SerT]):
                def post(self, parsed_body: Body[_ModT]) -> str:
                    ...

            class NativeBare(NativeController): ...
            """,
        ),
        ns,
    )

    reusable = ns['NativeController']
    assert reusable.is_abstract
    assert getattr(reusable, 'serializer', None) is None
    assert getattr(reusable, 'api_endpoints', None) is None

    concrete = ns['NativeBare']
    assert not concrete.is_abstract
    assert concrete.serializer is PydanticSerializer
    assert _body_models(concrete) == [_DefaultModel]
