# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/params.py
# under MIT license.

# Original license:
# https://github.com/litestar-org/litestar/blob/main/LICENSE

# The MIT License (MIT)

# Copyright (c) 2021, 2022, 2023, 2024, 2025, 2026 Litestar Org.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
