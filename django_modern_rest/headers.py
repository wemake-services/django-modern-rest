import dataclasses
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, final

from django_modern_rest.types import Empty, EmptyObj

if TYPE_CHECKING:
    from django_modern_rest.serialization import BaseSerializer


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

    __slots__ = ('deprecated', 'description', 'example')

    description: str | None
    deprecated: bool
    example: Any | None


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

    def to_description(self) -> 'HeaderDescription':
        """Convert header type."""
        return HeaderDescription(required=self.required)


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


def build_headers(
    headers: Mapping[str, NewHeader] | Empty,
    serializer: type['BaseSerializer'],
) -> dict[str, Any]:
    """Returns headers with values for raw data endpoints."""
    result_headers: dict[str, Any] = {'Content-Type': serializer.content_type}
    if isinstance(headers, Empty):
        return result_headers
    result_headers.update({
        header_name: response_header.value
        for header_name, response_header in headers.items()
    })
    return result_headers
