import abc
import json
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from django.core.serializers.json import DjangoJSONEncoder
from typing_extensions import override

from django_modern_rest.exceptions import (
    NotAcceptableError,
    ResponseSchemaError,
)
from django_modern_rest.metadata import (
    EndpointMetadata,
    ResponseSpec,
    ResponseSpecProvider,
)
from django_modern_rest.parsers import (
    JsonParser,
    Parser,
    _NoOpParser,  # pyright: ignore[reportPrivateUsage]
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.serializer import BaseSerializer


class Renderer(ResponseSpecProvider):
    """
    Base class for all renderer types.

    Subclass it to implement your own renderers.
    """

    __slots__ = ()

    content_type: str
    """
    Content-Type that this renderer works with.

    Must be defined for all subclasses.
    """

    @abc.abstractmethod
    def render(
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any],
    ) -> bytes:
        """Function to be called on object serialization."""

    @property
    @abc.abstractmethod
    def validation_parser(self) -> Parser:
        """
        Returns a parser that can parse what this renderer rendered.

        Why? Because when ``validate_responses`` is ``True``,
        we parse the response body once again to see if it fits the schema.

        That's why all renderers must know how to unparse its results.
        """
        raise NotImplementedError

    @override
    @classmethod
    def provide_response_specs(
        cls,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when data can't be rendered."""
        # This is technically not renderer's response, but it is the closest.
        response_validation = (
            cls._add_new_response(
                ResponseSpec(
                    return_type=controller_cls.error_model,
                    status_code=ResponseSchemaError.status_code,
                    description=(
                        'Raised when returned response does not '
                        'match the response schema'
                    ),
                ),
                existing_responses,
            )
            # When validation is disabled, `ResponseSchemaError` can't happen.
            if metadata.validate_responses
            else []
        )
        return [
            *response_validation,
            *cls._add_new_response(
                # When we face wrong `Accept` header, we raise 406 error:
                ResponseSpec(
                    return_type=controller_cls.error_model,
                    status_code=NotAcceptableError.status_code,
                    description=(
                        'Raised when provided `Accept` header '
                        'cannot be satisfied'
                    ),
                ),
                existing_responses,
            ),
        ]


class _DMREncoder(DjangoJSONEncoder):
    def __init__(
        self,
        *args: Any,
        serializer_hook: Callable[[Any], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._serializer_hook = serializer_hook

    @override
    def default(self, o: Any) -> Any:  # noqa: WPS111
        try:
            return super().default(o)
        except TypeError:
            if self._serializer_hook:
                return self._serializer_hook(o)
            raise


class JsonRenderer(Renderer):
    """
    Fallback implementation of a json renderer.

    Only is used when ``msgspec`` is not installed.

    .. warning::

        It is not recommended to be used directly.
        It is slow and has less features.
        We won't add any complex objects support to this renderer.

    """

    __slots__ = ('_encoder_cls',)

    content_type = 'application/json'
    """Works with ``json`` only."""

    def __init__(
        self,
        encoder_cls: type[DjangoJSONEncoder] = _DMREncoder,
    ) -> None:
        """Init the renderer with all defaults."""
        self._encoder_cls = encoder_cls

    @override
    def render(
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any],
    ) -> bytes:
        """
        Encode a value into JSON bytestring.

        Args:
            to_serialize: Value to encode.
            serializer_hook: Callable to support non-natively supported types.

        Returns:
            JSON as bytes.
        """
        # msgspec returns `bytes`, we prefer to use `bytes` by default
        # and not to create extra strings when not needed in "fast" mode.
        # We don't really care about raw json implementation. It is a fallback.
        return json.dumps(
            to_serialize,
            cls=self._encoder_cls,
            serializer_hook=serializer_hook,
        ).encode('utf8')

    @property
    @override
    def validation_parser(self) -> JsonParser:
        """Regular json parser can parse this."""
        return JsonParser()


class FileRenderer(Renderer):
    """
    Renders any file.

    Works with any files and any content types.

    .. warning::

        Works with any content type by default,
        so it must be an only renderer for the endpoint.

    """

    __slots__ = ('content_type',)

    def __init__(self, content_type: str = '*/*') -> None:
        """Users can customize content types that this renderer works with."""
        self.content_type = content_type

    @override
    def render(
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any],
    ) -> bytes:
        """Render a file."""
        raise NotImplementedError(
            'FileRenderer.render() must not be called, '
            'instead return a FileResponse directly',
        )

    @property
    @override
    def validation_parser(self) -> _NoOpParser:
        """Since there's nothing to parse, we return a no-op."""
        return _NoOpParser(self.content_type)
