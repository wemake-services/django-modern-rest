import dataclasses
from collections.abc import Callable
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, final

from django.http import HttpResponse

from django_modern_rest.exceptions import (
    ResponseSerializationError,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    DMR_VALIDATE_RESPONSE_KEY,
    resolve_setting,
)

if TYPE_CHECKING:
    from django_modern_rest.endpoint import EndpointMetadata

_ResponseT = TypeVar('_ResponseT', bound=HttpResponse)


class ResponseValidator:
    __slots__ = ('_method', '_serializer', 'metadata')

    # Public API:
    strict_validation: ClassVar[bool] = True

    def __init__(
        self,
        endpoint_func: Callable[..., Any],
        *,
        serializer: type[BaseSerializer],
    ) -> None:
        self._serializer = serializer
        # `Endpoint` adds `__metadata__` to all functions:
        self.metadata: EndpointMetadata = (
            endpoint_func.__endpoint__  # type: ignore[attr-defined]
        )
        self._method = HTTPMethod(endpoint_func.__name__.upper())

    def validate_response(self, response: _ResponseT) -> _ResponseT:
        """Validate ``.content`` of existing ``HttpResponse`` object."""
        if not resolve_setting(DMR_VALIDATE_RESPONSE_KEY):
            return response
        self._do_structured_validation(response.content, response=response)
        return response

    def validate_content(self, structured: Any) -> '_ValidationContext':
        """Validate *structured* data before dumping it to json."""
        all_response_data = _ValidationContext(
            raw_data=structured,
            status_code=self.metadata.status_code,
        )
        if not resolve_setting(DMR_VALIDATE_RESPONSE_KEY):
            return all_response_data
        self._do_structured_validation(structured)
        return all_response_data

    def _do_structured_validation(
        self,
        structured: Any | bytes,
        *,
        response: HttpResponse | None = None,
    ) -> None:
        """
        Does structured validation based on the provided schema.

        Can't be reached if ``validate_responses`` is set to ``False``.

        Args:
            structured: data to be validated.
            response: possible ``HttpResponse`` instance for validation.

        """
        if response:
            self.metadata.validate_for_response(response)
            structured = self._serializer.from_json(structured)

        try:
            self._serializer.from_python(
                structured,
                self.metadata.return_type,
                strict=self.strict_validation,
            )
        except self._serializer.validation_error as exc:
            raise ResponseSerializationError(
                self._serializer.error_to_json(exc),
            ) from None


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ValidationContext:
    """Combines all validated data together."""

    raw_data: Any  # not empty
    status_code: HTTPStatus
