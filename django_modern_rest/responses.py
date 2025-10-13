from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from django.http import HttpResponse
from typing_extensions import get_type_hints

from django_modern_rest.exceptions import (
    ResponseSerializationError,
    UnsolvableAnnotationsError,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    DMR_VALIDATE_RESPONSE_KEY,
    resolve_setting,
)
from django_modern_rest.types import Empty, EmptyObj

if TYPE_CHECKING:
    from django_modern_rest.endpoint import EndpointSpec

_ResponseT = TypeVar('_ResponseT', bound=HttpResponse)


class ResponseValidator:
    __slots__ = ('_metadata', '_return_annotation', '_serializer')

    def __init__(
        self,
        serializer: type[BaseSerializer],
        endpoint_func: Callable[..., Any],
        metadata: 'EndpointSpec | Empty',
    ) -> None:
        self._serializer = serializer
        self._metadata = metadata
        self._parse_annotations(endpoint_func)

    def validate_response(self, response: _ResponseT) -> _ResponseT:
        """Validate ``.content`` of existing ``HttpResponse`` object."""
        if not resolve_setting(DMR_VALIDATE_RESPONSE_KEY):
            return response
        self._do_structured_validation(response.content, load=True)
        return response

    def validate_content(self, structured: Any) -> Any:
        """Validate *structured* data before dumping it to json."""
        if not resolve_setting(DMR_VALIDATE_RESPONSE_KEY):
            return structured
        self._do_structured_validation(structured)
        return structured

    def _do_structured_validation(
        self,
        structured: Any | bytes,
        *,
        load: bool = False,
    ) -> None:
        """
        Does structured validation based on the provided schema.

        Can't be reached if ``validate_responses`` is set to ``False``.

        Args:
            structured: data to be validated.
            load: pass when *structured* is of type ``bytes`` to load into json.

        """
        if load:
            structured = self._serializer.from_json(structured)

        model = (
            self._metadata.return_type
            if (
                not isinstance(self._metadata, Empty)
                and not isinstance(self._metadata.return_type, Empty)
            )
            else self._return_annotation
        )
        try:
            self._serializer.from_python(structured, model)
        except self._serializer.validation_error as exc:
            raise ResponseSerializationError(str(exc)) from exc

    def _parse_annotations(self, endpoint_func: Callable[..., Any]) -> None:
        if self._metadata and self._metadata.return_type is not EmptyObj:
            # We don't want to parse annotation, since it is slow and can
            # raise potential errors, so just set it to empty.
            self._return_annotation = EmptyObj
            return

        try:
            self._return_annotation = get_type_hints(
                endpoint_func,
            ).get('return', EmptyObj)
        except TypeError as exc:
            raise UnsolvableAnnotationsError(
                f'Annotations of {endpoint_func!r} cannot be solved',
            ) from exc

        if self._return_annotation is EmptyObj:
            raise UnsolvableAnnotationsError(
                f'Function {endpoint_func!r} is missing return type annotation',
            )
