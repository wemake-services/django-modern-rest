import pytest

from django_modern_rest import Body, Headers, Query


def test_validate_components_type_params() -> None:
    """Ensure that we need at least one type param for component."""
    for component_cls in (Headers, Body, Query):
        with pytest.raises(TypeError):
            component_cls[*()]  # pyright: ignore[reportInvalidTypeArguments]
