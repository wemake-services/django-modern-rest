import dataclasses
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:
    from django_modern_rest.response import ResponseModification
    from django_modern_rest.serialization import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True, init=False)
class _BaseResponseHeader:
    """
    Abstract base class that represents an HTTP header in the response.

    It will be later transformed into
    https://spec.openapis.org/oas/v3.1.0#parameterObject for doc purposes.

    Attributes:
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
    example: str | None = None


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NewHeader(_BaseResponseHeader):
    """
    New header that will be added to :class:`django.http.HttpResponse` by us.

    This class is used to add new entries to response's headers.
    Is not used for validation.
    """

    value: str  # noqa: WPS110

    def to_spec(self) -> 'HeaderSpec':
        """Convert header type."""
        namespace = dataclasses.asdict(self)
        namespace.pop('value')
        return HeaderSpec(**namespace, required=True)


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class HeaderSpec(_BaseResponseHeader):
    """
    Existing header that :class:`django.http.HttpResponse` already has.

    This class is used to describe the existing reality.
    Used for validation that all ``required`` headers are present.
    """

    required: bool = True


def build_headers(
    modification: 'ResponseModification',
    serializer: type['BaseSerializer'],
) -> dict[str, str]:
    """Returns headers with values for raw data endpoints."""
    result_headers: dict[str, Any] = {'Content-Type': serializer.content_type}
    if not modification.headers:
        return result_headers
    result_headers.update({
        header_name: response_header.value
        for header_name, response_header in modification.headers.items()
    })
    return result_headers
