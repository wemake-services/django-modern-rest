import sys
import textwrap
from typing import Generic, TypeVar

import pydantic
import pytest

from dmr import Body, Controller
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)
_ModelT = TypeVar('_ModelT')
_OtherT = TypeVar('_OtherT')
_ExtraT = TypeVar('_ExtraT')


class _BodyModel(pydantic.BaseModel):
    user: str


def test_several_layers() -> None:
    """Ensure that we can support reusable generic controllers."""

    class _RegularType:
        """Is only needed for extra complexity."""

    class _BaseController(
        Controller[_SerializerT],
        Generic[_SerializerT, _ModelT],
    ):
        def post(self, parsed_body: Body[_ModelT]) -> str:
            raise NotImplementedError

    assert _BaseController.is_abstract

    class ReusableController(
        _RegularType,
        _BaseController[_SerializerT, _ModelT],
    ):
        """Some framework can provide such a type."""

    assert ReusableController.is_abstract

    class OurController(
        ReusableController[PydanticSerializer, _BodyModel],
    ):
        """Intermediate level."""

    assert not OurController.is_abstract
    assert OurController.serializer is PydanticSerializer
    metadata = OurController.api_endpoints['POST'].metadata
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == _BodyModel

    class ReusableWithExtraType(
        _BaseController[_SerializerT, _ModelT],
        _RegularType,
        # Order is a bit different on purpose:
        Generic[_SerializerT, _ExtraT, _ModelT],
    ):
        """Adding extra type vars just for the complexity."""

    class FinalController(
        ReusableWithExtraType[PydanticSerializer, str, _BodyModel],
    ):
        """Final level."""

    assert not FinalController.is_abstract
    assert FinalController.serializer is PydanticSerializer
    metadata = FinalController.api_endpoints['POST'].metadata
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == _BodyModel


def test_generic_parser_in_concrete_controller() -> None:
    """Ensure that we can't have generic parsers in concrente controllers."""

    class _BaseController(
        Controller[_SerializerT],
        Generic[_SerializerT, _ModelT],
    ):
        def post(self, parsed_body: Body[_ModelT]) -> str:
            raise NotImplementedError

    with pytest.raises(UnsolvableAnnotationsError, match='must be concrete'):

        class ConcreteController(_BaseController[PydanticSerializer, _ModelT]):
            """Must raise."""


@pytest.mark.skipif(
    sys.version_info < (3, 12),
    reason='PEP-695 was added in 3.12',
)
def test_pep695_type_params() -> None:  # pragma: no cover
    """Ensure that PEP-695 syntax is supported on 3.12+."""
    # We have to use `exec` here, because 3.12+ syntax
    # will cause `SyntaxError` for the whole test module.
    ns = globals().copy()  # noqa: WPS421
    exec(  # noqa: S102, WPS421
        textwrap.dedent(
            """
            class _BaseController[_S: BaseSerializer, _M](
                Controller[_S],
            ):
                def post(self, parsed_body: Body[_M]) -> str:
                    ...
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
            ): ...
            """,
        ),
        ns,
    )

    controller = ns['OurController']
    assert not controller.is_abstract
    assert controller.serializer is PydanticSerializer
    metadata = controller.api_endpoints['POST'].metadata
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == _BodyModel
