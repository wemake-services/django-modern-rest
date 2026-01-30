# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/params.py
# under MIT license.
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class KwargDefinition:
    """Data container representing a constrained kwarg."""

    # TODO: use type/dataclass for examples
    examples: list[dict[str, Any]] | None = None
    # TODO: use type/dataclass for external docs
    external_docs: dict[str, Any] | None = None
    content_encoding: str | None = None
    default: Any = None
    title: str | None = None
    description: str | None = None
    const: bool | None = None
    gt: float | None = None
    ge: float | None = None
    lt: float | None = None
    le: float | None = None
    multiple_of: float | None = None
    min_items: int | None = None
    max_items: int | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    lower_case: bool | None = None
    upper_case: bool | None = None
    format: str | None = None
    enum: Sequence[Any] | None = None
    read_only: bool | None = None
    schema_extra: dict[str, Any] | None = None
    schema_component_key: str | None = None
    include_in_schema: bool = True


@dataclass(slots=True, frozen=True)
class FieldDefinition:
    """Definition of a field in the OpenAPI."""

    name: str
    annotation: Any
    default: Any = None
    extra_data: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    kwarg_definition: KwargDefinition | None = None
