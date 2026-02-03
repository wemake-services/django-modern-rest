import abc
import json
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar

from django.core.serializers.json import DjangoJSONEncoder
from typing_extensions import override

from django_modern_rest.exceptions import NotAcceptableError
from django_modern_rest.metadata import ResponseSpec, ResponseSpecProvider

if TYPE_CHECKING:
    from django_modern_rest.serializer import BaseSerializer


class Renderer(ResponseSpecProvider):
    """
    Base class for all renderer types.

    Subclass it to implement your own renderers.
    """

    __slots__ = ()

    content_type: ClassVar[str]
    """
    Content-Type that this renderer works with.

    Must be defined for all subclasses.
    """

    @classmethod
    @abc.abstractmethod
    def render(
        cls,
        to_serialize: Any,
        serializer: Callable[[Any], Any],
    ) -> bytes:
        """Function to be called on object serialization."""

    @override
    @classmethod
    def provide_response_specs(
        cls,
        serializer: type['BaseSerializer'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when data can't be rendered."""
        return cls._add_new_response(
            # When we face wrong `Accept` header, we raise 406 error:
            ResponseSpec(
                return_type=serializer.default_error_model,
                status_code=NotAcceptableError.status_code,
                description=(
                    'Raised when provided `Accept` header cannot be satisfied'
                ),
            ),
            existing_responses,
        )


class _DMREncoder(DjangoJSONEncoder):
    def __init__(
        self,
        *args: Any,
        serializer: Callable[[Any], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._serializer = serializer

    @override
    def default(self, o: Any) -> Any:  # noqa: WPS111
        try:
            return super().default(o)
        except TypeError:
            if self._serializer:
                return self._serializer(o)
            raise


class JsonRenderer(Renderer):
    """
    Fallback implementation of a json renderer.

    Only is used when ``msgspec`` is not installed.

    .. warning::

        It is not recommended to be used directly.
        It is slow and has less features.

    """

    __slots__ = ()

    content_type: ClassVar[str] = 'application/json'
    """Works with ``json`` only."""

    _encoder_cls: ClassVar[type[DjangoJSONEncoder]] = _DMREncoder

    @override
    @classmethod
    def render(
        cls,
        to_serialize: Any,
        serializer: Callable[[Any], Any],
    ) -> bytes:
        """
        Encode a value into JSON bytestring.

        Args:
            to_serialize: Value to encode.
            serializer: Callable to support non-natively supported types.

        Returns:
            JSON as bytes.
        """
        # msgspec returns `bytes`, we prefer to use `bytes` by default
        # and not to create extra strings when not needed in "fast" mode.
        # We don't really care about raw json implementation. It is a fallback.
        return json.dumps(
            to_serialize,
            cls=cls._encoder_cls,
            serializer=serializer,
        ).encode('utf8')
