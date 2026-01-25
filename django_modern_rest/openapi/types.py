# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/params.py
# under MIT license.
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from django_modern_rest.types import Empty, EmptyObj


@dataclass(frozen=True)
class KwargDefinition:
    """Data container representing a constrained kwarg."""

    # TODO: use type/dataclass for examples
    examples: list[dict[str, Any]] | None = field(default=None)
    """A list of Example models."""
    # TODO: use type/dataclass for external docs
    external_docs: dict[str, Any] | None = field(default=None)
    """A url pointing at external documentation for the given parameter."""
    content_encoding: str | None = field(default=None)
    """The content encoding of the value.

    Applicable on to string values. See OpenAPI 3.1 for details.
    """
    default: Any = field(default=Empty)
    """A default value.

    If const is true, this value is required.
    """
    title: str | None = field(default=None)
    """
    String value used in the title section of the OpenAPI schema for the
    given parameter.
    """
    description: str | None = field(default=None)
    """
    String value used in the description section of the OpenAPI schema for the
    given parameter.
    """
    const: bool | None = field(default=None)
    """A boolean flag dictating whether this parameter is a constant.

    If True, the value passed to the parameter must equal its default value.
    This also causes the OpenAPI const field to be populated with the default
    value.
    """
    gt: float | None = field(default=None)
    """Constrict value to be greater than a given float or int.

    Equivalent to exclusiveMinimum in the OpenAPI specification.
    """
    ge: float | None = field(default=None)
    """Constrict value to be greater or equal to a given float or int.

    Equivalent to minimum in the OpenAPI specification.
    """
    lt: float | None = field(default=None)
    """Constrict value to be less than a given float or int.

    Equivalent to exclusiveMaximum in the OpenAPI specification.
    """
    le: float | None = field(default=None)
    """Constrict value to be less or equal to a given float or int.

    Equivalent to maximum in the OpenAPI specification.
    """
    multiple_of: float | None = field(default=None)
    """Constrict value to a multiple of a given float or int.

    Equivalent to multipleOf in the OpenAPI specification.
    """
    min_items: int | None = field(default=None)
    """Constrict a set or a list to have a minimum number of items.

    Equivalent to minItems in the OpenAPI specification.
    """
    max_items: int | None = field(default=None)
    """Constrict a set or a list to have a maximum number of items.

    Equivalent to maxItems in the OpenAPI specification.
    """
    min_length: int | None = field(default=None)
    """Constrict a string or bytes value to have a minimum length.

    Equivalent to minLength in the OpenAPI specification.
    """
    max_length: int | None = field(default=None)
    """Constrict a string or bytes value to have a maximum length.

    Equivalent to maxLength in the OpenAPI specification.
    """
    pattern: str | None = field(default=None)
    """
    A string representing a regex against which the given string will be
    matched.

    Equivalent to pattern in the OpenAPI specification.
    """
    lower_case: bool | None = field(default=None)
    """Constrict a string value to be lower case."""
    upper_case: bool | None = field(default=None)
    """Constrict a string value to be upper case."""
    format: str | None = field(default=None)
    """Specify the format to which a string value should be converted."""
    enum: Sequence[Any] | None = field(default=None)
    """A sequence of valid values."""
    read_only: bool | None = field(default=None)
    """A boolean flag dictating whether this parameter is read only."""
    schema_extra: dict[str, Any] | None = field(default=None)
    """Extensions to the generated schema.

    If set, will overwrite the matching fields in the generated schema.

    .. versionadded:: 2.8.0
    """
    schema_component_key: str | None = None
    """
    Use as the key for the reference when creating a component for this type
    .. versionadded:: 2.12.0
    """
    include_in_schema: bool = True
    """
    A boolean flag dictating whether this parameter should be included in the
    schema.

    .. versionadded:: 2.17.0
    """


@dataclass(slots=True, frozen=True)
class FieldDefinition:
    """Definition of a field in the API."""

    name: str
    default: Any | Empty = EmptyObj
    extra_data: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    kwarg_definition: KwargDefinition | None = field(default=None)
