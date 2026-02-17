import dataclasses
from typing import TYPE_CHECKING, Any, ClassVar, Literal, final

if TYPE_CHECKING:
    from dmr.metadata import ResponseModification
    from dmr.renderers import Renderer


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True, init=False)
class _BaseResponseHeader:
    """
    Abstract base class that represents an HTTP header in the response.

    It will be later transformed into
    https://spec.openapis.org/oas/v3.1.0#parameterObject for doc purposes.
    """

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

    Attributes:
        description: Documentation, why this header is needed and what it does.
        deprecated: Whethere this header is deprecated.
        example: Documentation, what can be given as values in this header.
        value: value to be set in this new header.

    """

    is_actionable: ClassVar[Literal[True]] = True

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

    Attributes:
        description: Documentation, why this header is needed and what it does.
        deprecated: Whethere this header is deprecated.
        example: Documentation, what can be given as values in this header.
        required: Whether or not this header can be missing.
        schema_only: Is true, when header is only used for schema purposes,
            without any runtime validation. This might be useful, when
            this header will be set after our framework's validation.
            For example,
            by :class:`django.contrib.sessions.middleware.SessionMiddleware`
            or by HTTP proxy.

    """

    is_actionable: ClassVar[Literal[False]] = False

    required: bool = True
    schema_only: bool = False

    def to_spec(self) -> 'HeaderSpec':
        """Needed for API compat with `NewHeader`."""
        return self


def build_headers(
    modification: 'ResponseModification',
    renderer: 'Renderer',
) -> dict[str, str]:
    """Returns headers with values for raw data endpoints."""
    result_headers: dict[str, Any] = {'Content-Type': renderer.content_type}
    headers = modification.actionable_headers()
    if not headers:
        return result_headers
    result_headers.update({
        header_name: response_header.value
        for header_name, response_header in headers.items()
    })
    return result_headers
