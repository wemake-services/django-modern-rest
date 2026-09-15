import pytest

from dmr.openapi.objects import (
    MediaType,
    OpenAPIType,
    Parameter,
    Reference,
    Schema,
)


def _form_content() -> dict[str, MediaType | Reference]:
    return {'application/x-www-form-urlencoded': MediaType(schema=Schema())}


def test_querystring_parameter() -> None:
    """Ensure that a 3.2 whole-query-string parameter can be created."""
    form_content = _form_content()

    parameter = Parameter(
        name='filter',
        param_in='querystring',
        content=form_content,
    )

    assert parameter.schema is None
    assert parameter.content == form_content


def test_querystring_parameter_without_content() -> None:
    """Ensure that a query string parameter cannot be schema-only."""
    with pytest.raises(ValueError, match='must use `content`'):
        Parameter(
            name='filter',
            param_in='querystring',
            schema=Schema(type=OpenAPIType.OBJECT),
        )


def test_querystring_parameter_with_both() -> None:
    """Ensure that a query string parameter cannot also have a schema."""
    with pytest.raises(ValueError, match='must use `content`'):
        Parameter(
            name='filter',
            param_in='querystring',
            schema=Schema(type=OpenAPIType.OBJECT),
            content=_form_content(),
        )


def test_regular_parameters_still_use_schema() -> None:
    """Ensure that we only validate `querystring` parameters."""
    parameter = Parameter(
        name='search',
        param_in='query',
        schema=Schema(type=OpenAPIType.STRING),
    )

    assert parameter.content is None
