from typing import Annotated, Any, Optional, Union

import pydantic
import pytest
from typing_extensions import TypeAliasType

from dmr import Body, Controller, Query
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer


class _Model(pydantic.BaseModel):
    name: str


_OptionalBody = TypeAliasType('_OptionalBody', Optional[Body[_Model]])  # noqa: UP045


@pytest.mark.parametrize(
    'annotation',
    [
        Body[_Model] | None,
        Union[Body[_Model], str],  # noqa: UP007
        Body[_Model] | str,
        Optional[Body[_Model]],  # noqa: UP045
        list[Body[_Model]],
        dict[str, Body[_Model]],
        dict[Body[str], _Model],
        Annotated[Body[_Model] | None, 'metadata'],
        _OptionalBody,
    ],
)
def test_hidden_component_annotation(annotation: Any) -> None:
    """Ensures that components hidden inside other types are not allowed."""
    with pytest.raises(
        UnsolvableAnnotationsError,
        match='has a component hidden inside',
    ):

        class _Controller(Controller[PydanticSerializer]):
            def post(self, parsed_body: annotation = None) -> str:  # pyright: ignore[reportInvalidTypeForm]
                raise NotImplementedError


@pytest.mark.parametrize(
    'annotation',
    [
        str,
        dict[str, Any],
        _Model,
        _Model | None,
    ],
)
def test_regular_parameters_are_allowed(annotation: Any) -> None:
    """Ensures that regular parameters with defaults are not components."""

    class _Controller(Controller[PydanticSerializer]):
        def get(
            self,
            parsed_query: Query[_Model | None] = None,
            help_text: annotation = None,  # pyright: ignore[reportInvalidTypeForm]
        ) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0].default is None


def test_optional_inside_component_is_allowed() -> None:
    """Ensures that `Query[Model | None] = None` is the correct form."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self, parsed_query: Query[_Model | None] = None) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.component_parsers[0].default is None
