import sys
import textwrap
from typing import Any, Generic, TypeVar

import pydantic
import pytest

from django_modern_rest import Blueprint, Body, Controller
from django_modern_rest.exceptions import UnsolvableAnnotationsError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.routing import compose_blueprints
from django_modern_rest.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=type[BaseSerializer])
_ModelT = TypeVar('_ModelT')
_OtherT = TypeVar('_OtherT')
_ExtraT = TypeVar('_ExtraT')


class _BodyModel(pydantic.BaseModel):
    user: str


@pytest.mark.parametrize(
    'generic_type',
    [
        [],
        [Generic[_SerializerT, _ModelT]],  # type: ignore[index]
    ],
)
def test_several_layers(generic_type: list[Any]) -> None:
    """Ensure that we can support reusable generic controllers."""

    class _RegularType:
        """Is only needed for extra complexity."""

    class _BaseController(
        Controller[_SerializerT],  # type: ignore[type-var]
        Body[_ModelT],
        *generic_type,  # type: ignore[misc]  # noqa: WPS606
    ):
        """Intermediate controller type."""

    class ReusableController(
        _RegularType,
        _BaseController[_SerializerT, _ModelT],
    ):
        """Some framework can provide such a type."""

    class OurController(
        ReusableController[PydanticSerializer, _BodyModel],  # type: ignore[type-var]
    ):
        def post(self) -> str:
            raise NotImplementedError

    assert OurController.serializer is PydanticSerializer
    metadata = OurController.api_endpoints['POST'].metadata
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == (_BodyModel,)

    class ReusableWithExtraType(
        _BaseController[_SerializerT, _ModelT],
        _RegularType,
        # Order is a bit different on purpose:
        Generic[_SerializerT, _ExtraT, _ModelT],
    ):
        """Adding extra type vars just for the complexity."""

    class FinalController(
        ReusableWithExtraType[PydanticSerializer, str, _BodyModel],  # type: ignore[type-var]
    ):
        def post(self) -> str:
            raise NotImplementedError

    assert FinalController.serializer is PydanticSerializer
    metadata = FinalController.api_endpoints['POST'].metadata
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == (_BodyModel,)


def test_generic_blueprint() -> None:
    """Ensure that we can use reusable generic blueprints."""

    class _ReusableBlueprint(
        Blueprint[_SerializerT],  # type: ignore[type-var]
        Body[_ModelT],
    ):
        """Base blueprint to be reused."""

    class _ImplementedBlueprint(
        _ReusableBlueprint[_SerializerT, _OtherT],
    ):
        def post(self) -> str:
            raise NotImplementedError

    class ExposedBlueprint(
        _ImplementedBlueprint[_ExtraT, _BodyModel],  # type: ignore[type-var]
    ):
        """Does nothing, just messes up some type vars."""

    class OurBlueprint(ExposedBlueprint[PydanticSerializer]):
        """Ready to be used."""

    assert OurBlueprint.serializer is PydanticSerializer
    controller = compose_blueprints(OurBlueprint)
    metadata = controller.api_endpoints['POST'].metadata
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == (_BodyModel,)


def test_generic_parser_in_concrete_controller() -> None:
    """Ensure that we can't have generic parsers in concrente controllers."""

    class _BaseController(
        Controller[_SerializerT],  # type: ignore[type-var]
        Body[_ModelT],
    ):
        """Intermediate controller type."""

    with pytest.raises(UnsolvableAnnotationsError, match='must be concrete'):

        class ConcreteController(
            _BaseController[PydanticSerializer, _ModelT],  # type: ignore[type-var]
        ):
            def post(self) -> str:
                raise NotImplementedError


@pytest.mark.skipif(
    sys.version_info < (3, 12),
    reason='PEP-695 was added in 3.12',
)
def test_pep695_type_params() -> None:
    """Ensure that PEP-695 syntax is supported on 3.12+."""
    # We have to use `exec` here, because 3.12+ syntax
    # will cause `SyntaxError` for the whole test module.
    ns = globals().copy()  # noqa: WPS421
    exec(  # noqa: S102, WPS421
        textwrap.dedent(
            """
            class _BaseController[_S: BaseSerializer, _M](
                Controller[_S],
                Body[_M],
            ): ...
            """,
        ),
        ns,
    )

    exec(  # noqa: S102, WPS421
        textwrap.dedent(
            """class ReusableController[_SerT: BaseSerializer, _ModelT](
                _BaseController[_SerT, _ModelT],
            ): ...
            """,
        ),
        ns,
    )

    exec(  # noqa: S102, WPS421
        textwrap.dedent(
            """
            class OurController(
                ReusableController[PydanticSerializer, _BodyModel],
            ):
                def post(self) -> str:
                    raise NotImplementedError
            """,
        ),
        ns,
    )

    controller = ns['OurController']
    assert controller.serializer is PydanticSerializer
    metadata = controller.api_endpoints['POST'].metadata
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == (_BodyModel,)
