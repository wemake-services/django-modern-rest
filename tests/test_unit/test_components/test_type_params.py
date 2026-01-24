import pytest

from django_modern_rest import Body, Controller, Headers, Query
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer


def test_validate_components_type_params() -> None:
    """Ensure that we need at least one type param for component."""
    for component_cls in (Headers, Body, Query):
        with pytest.raises(TypeError):
            component_cls[  # pyright: ignore[reportInvalidTypeArguments]
                *()  # pyrefly: ignore[not-a-type]
            ]

    for component_cls in (Headers, Body, Query):
        with pytest.raises(TypeError):
            component_cls[  # pyrefly: ignore[bad-specialization]  # pyright: ignore[reportInvalidTypeArguments]  # noqa: E501
                int,
                str,
            ]


def test_validate_headers_zero_params() -> None:
    """Ensure that we need at least one type param for component."""
    with pytest.raises(EndpointMetadataError, match='_WrongHeaders'):

        class _WrongHeaders(
            Headers,  # type: ignore[type-arg]
            Controller[PydanticSerializer],
        ):
            def get(self) -> dict[str, str]:
                raise NotImplementedError


def test_validate_body_zero_params() -> None:
    """Ensure that we need at least one type param for component."""
    with pytest.raises(EndpointMetadataError, match='_WrongBody'):

        class _WrongBody(
            Body,  # type: ignore[type-arg]
            Controller[PydanticSerializer],
        ):
            def get(self) -> dict[str, str]:
                raise NotImplementedError


def test_validate_query_zero_params() -> None:
    """Ensure that we need at least one type param for component."""
    with pytest.raises(EndpointMetadataError, match='_WrongQuery'):

        class _WrongQuery(
            Query,  # type: ignore[type-arg]
            Controller[PydanticSerializer],
        ):
            def get(self) -> dict[str, str]:
                raise NotImplementedError
