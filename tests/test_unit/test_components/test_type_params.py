import textwrap
from typing import Any

import pytest

from dmr import Body, Controller, Cookies, FileMetadata, Headers, Path, Query
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer


@pytest.mark.parametrize(
    'component_cls',
    [
        Headers,
        Body,
        Query,
        FileMetadata,
        Path,
        Cookies,
    ],
)
def test_validate_components_type_params(
    *,
    component_cls: type[Any],
) -> None:
    """Ensure that we need at least one type param for component."""
    with pytest.raises(TypeError):
        component_cls[*()]  # pyright: ignore[reportIndexIssue]

    with pytest.raises(TypeError):
        component_cls[int, str]  # pyright: ignore[reportIndexIssue]


@pytest.mark.parametrize(
    ('param_name', 'component'),
    [
        ('parsed_headers', 'Headers'),
        ('parsed_query', 'Query'),
        ('parsed_body', 'Body'),
        ('parsed_cookies', 'Cookies'),
        ('parsed_path', 'Path'),
        ('parsed_file_metadata', 'FileMetadata'),
    ],
)
@pytest.mark.parametrize(
    'base',
    [Controller[PydanticSerializer]],
)
def test_validate_component_zero_params(
    *,
    base: type[Any],
    param_name: str,
    component: str,
) -> None:
    """Ensure that we need at least one type param for component."""
    with pytest.raises(
        UnsolvableAnnotationsError,
        match='Cannot solve type annotations',
    ):
        exec(  # noqa: S102, WPS421
            textwrap.dedent(
                f"""
                class _Wrong(base):
                    def get(self, {param_name}: {component}) -> str:
                        raise NotImplementedError
                """,
            ),
            globals().copy(),  # noqa: WPS421
            locals().copy(),  # noqa: WPS421
        )


@pytest.mark.parametrize(
    ('param_name', 'component'),
    [
        ('wrong', 'Headers'),
        ('wrong', 'Query'),
        ('wrong', 'Body'),
        ('wrong', 'Cookies'),
        ('wrong', 'Path'),
        ('wrong', 'FileMetadata'),
    ],
)
@pytest.mark.parametrize(
    'base',
    [Controller[PydanticSerializer]],
)
def test_validate_component_param_name(
    *,
    base: type[Any],
    param_name: str,
    component: str,
) -> None:
    """Ensure that we need a correct parameter name for a component."""
    with pytest.raises(UnsolvableAnnotationsError, match="not 'wrong'"):
        exec(  # noqa: S102, WPS421
            textwrap.dedent(
                f"""
                class _Wrong(base):
                    def get(self, {param_name}: {component}[str]) -> str:
                        raise NotImplementedError
                """,
            ),
            globals().copy(),  # noqa: WPS421
            locals().copy(),  # noqa: WPS421
        )
