from typing import Any

import pytest

from dmr import (
    Blueprint,
    Body,
    Controller,
    Cookies,
    Headers,
    Path,
    Query,
)
from dmr.exceptions import (
    UnsolvableAnnotationsError,
)
from dmr.plugins.pydantic import PydanticSerializer


def test_validate_components_type_params() -> None:
    """Ensure that we need at least one type param for component."""
    for component_cls in (Headers, Body, Query):
        with pytest.raises(TypeError):
            component_cls[*()]  # pyright: ignore[reportInvalidTypeArguments]

    for component_cls in (Headers, Body, Query):
        with pytest.raises(TypeError):
            component_cls[int, str]  # pyright: ignore[reportInvalidTypeArguments]


@pytest.mark.parametrize(
    'component',
    [
        Headers,
        Query,
        Body,
        Cookies,
        Path,
    ],
)
@pytest.mark.parametrize(
    'base',
    [
        Controller[PydanticSerializer],
        Blueprint[PydanticSerializer],
    ],
)
def test_validate_component_zero_params(
    base: type[Any],
    component: type[Any],
) -> None:
    """Ensure that we need at least one type param for component."""
    with pytest.raises(UnsolvableAnnotationsError, match='given 0'):

        class _Wrong(
            base,  # type: ignore[misc]
            component,  # type: ignore[misc]
        ):
            def get(self) -> dict[str, str]:
                raise NotImplementedError

    class ExtraLayer(component):  # type: ignore[misc]
        """Just to create an extra layer between controller and a component."""

    with pytest.raises(UnsolvableAnnotationsError, match='given 0'):

        class _WrongWithLayer(
            ExtraLayer,
            base,  # type: ignore[misc]
        ):
            def get(self) -> dict[str, str]:
                raise NotImplementedError
