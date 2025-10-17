import dataclasses
from collections.abc import Mapping
from typing import Any, ClassVar, TypeAlias, final

from django_modern_rest.types import Empty, EmptyObj


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _BaseResponseHeader:
    """
    Abstract base class that represents an HTTP header in the response.

    It will be later transformed into
    https://spec.openapis.org/oas/v3.1.0#parameterObject for doc purposes.

    Attrs:
        value: Optional value that can be added to the response headers.
        description: Documentation, why this header is needed and what it does.
        required: Whether this header is required or optional.
        deprecated: Whethere this header is deprecated.
        example: Documentation, what can be given as values in this header.

    """

    # TODO: re-enable schema, examples, content
    # TODO: make `examples` and `example` validation
    # TODO: make sure that we can't set fields like `explode`
    # to other values except default

    description: str | None = None
    deprecated: bool = False
    example: Any | None = None


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NewHeader(_BaseResponseHeader):
    """
    New header that will be added to :class:`django.http.HttpResponse` by us.

    This class is used to add new entries to response's headers.
    Is not used for validation.
    """

    # All new headers are required implicitly,
    # because they are always added to the response object by us.
    required: ClassVar[bool] = True
    # But they can add an exact value from the spec.
    value: str  # noqa: WPS110


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class HeaderDescription(_BaseResponseHeader):
    """
    Existing header that :class:`django.http.HttpResponse` already has.

    This class is used to describe the existing reality.
    Used for validation that all ``required`` headers are present.
    """

    # Does not have a value.
    value: ClassVar[Empty] = EmptyObj  # noqa: WPS110
    # But it's "required" state can be customized.
    required: bool = True


#: Type of all possible return headers.
ResponseHeadersT: TypeAlias = (
    Mapping[str, NewHeader] | Mapping[str, HeaderDescription]
)
