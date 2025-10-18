import abc
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, cast, final

from django.http import HttpHeaders, HttpRequest
from typing_extensions import TypedDict

from django_modern_rest.exceptions import (
    RequestSerializationError,
    ResponseSerializationError,
)

if TYPE_CHECKING:
    from django_modern_rest.internal.json import FromJson
    from django_modern_rest.metadata import EndpointMetadata

_ModelT = TypeVar('_ModelT')


class BaseSerializer:
    """Abstract base class for JSON serialization."""

    __slots__ = ()

    # API that needs to be set in subclasses:
    validation_error: ClassVar[type[Exception]]
    optimizer: ClassVar[type['BaseEndpointOptimizer']]

    # API that have defaults:
    content_type: ClassVar[str] = 'application/json'

    @classmethod
    @abc.abstractmethod
    def to_json(cls, structure: Any) -> bytes:
        """Convert structured data to json bytestring."""
        raise NotImplementedError

    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        """
        Customize how some objects are serialized into json.

        Only add types that are common for all potential plugins here.
        Should be called inside :meth:`to_json`.
        """
        if isinstance(to_serialize, HttpHeaders):
            return dict(to_serialize)
        raise ResponseSerializationError(
            f'Value {to_serialize} of type {type(to_serialize)} '
            'is not supported',
        )

    @classmethod
    @abc.abstractmethod
    def from_json(cls, buffer: 'FromJson') -> Any:
        """Convert json bytestring to structured data."""
        raise NotImplementedError

    @classmethod
    def deserialize_hook(
        cls,
        target_type: type[Any],
        to_deserialize: Any,
    ) -> Any:  # pragma: no cover
        """
        Customize how some objects are deserialized from json.

        Only add types that are common for all potential plugins here.
        Should be called inside :meth:`from_json`.
        """
        raise RequestSerializationError(
            f'Value {to_deserialize} of type {type(to_deserialize)} '
            f'is not supported for {target_type}',
        )

    @classmethod
    @abc.abstractmethod
    def from_python(
        cls,
        unstructured: Any,
        model: Any,
        *,
        strict: bool,
    ) -> Any:
        """
        Parse *unstructured* data from python primitives into *model*.

        Args:
            unstructured: Python objects to be parsed / validated.
            model: Python type to serve as a model.
                Can be any type hints that user can theoretically supply.
                Depends on the serialization plugin.
            strict: Whether we use more strict validation rules.
                For example, it is fine for a request validation
                to be less strict in some cases and allow type coercition.
                But, response types need to be strongly validated.

        Raises:
            validation_error: When parsing can't be done.

        Returns:
            Structured and validated data.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def error_to_json(cls, error: Exception) -> Any:
        """Serialize an exception to json the best way possible."""


class BaseEndpointOptimizer:
    """
    Plugins might often need to run some specific preparations for endpoints.

    To achieve that we provide an explicit API for that.
    """

    @classmethod
    @abc.abstractmethod
    def optimize_endpoint(cls, metadata: 'EndpointMetadata') -> None:
        """
        Optimize the endpoint.

        Args:
            metadata: Endpoint metadata to optimize.

        """


@final
@dataclass(slots=True, frozen=True, kw_only=True)
class _ComponentSpec:
    name: str
    data_getter: Any
    model: Any
    strict: bool


@final
@dataclass(slots=True, frozen=True, kw_only=True)
class SerializerContext:  # noqa: WPS214
    """Parse and bind request components for a controller.

    This context collects raw data for all registered components, validates
    the combined payload in a single call using a cached TypedDict model,
    and then binds the parsed values back to the controller.
    """

    _specs: tuple[_ComponentSpec, ...]
    _serializer: type[BaseSerializer]
    _combined_model: Any

    def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate provided context mapping and return parsed values."""
        return self._validate_context(context)

    def parse_and_bind(
        self,
        controller: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Collect, validate, and bind component data to the controller."""
        context = self._collect_context(controller, request, *args, **kwargs)
        validated = self(context)
        self._bind_parsed(controller, validated)

    @classmethod
    def build_for_class(
        cls,
        controller_cls: type[Any],
        serializer: type[BaseSerializer],
    ) -> 'SerializerContext':
        """Eagerly build context for a given controller and serializer."""
        specs, type_map = _build_type_map(controller_cls, serializer)

        combined_name = f'_{controller_cls.__qualname__}@ContextModel'
        CombinedModel = TypedDict(combined_name, type_map, total=True)  # type: ignore[misc]

        return SerializerContext(
            _specs=tuple(specs),
            _serializer=serializer,
            _combined_model=CombinedModel,
        )

    def _collect_context(
        self,
        controller: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Collect raw data for all components into a mapping."""
        context: dict[str, Any] = {}
        for spec in self._specs:
            raw = spec.data_getter(
                controller,
                self._serializer,
                (spec.model,),
                request,
                *args,
                **kwargs,
            )
            context[spec.name] = raw
        return context

    def _validate_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate the combined payload using the cached TypedDict model."""
        try:
            return self._validate_via_serializer(context)
        except self._serializer.validation_error as exc:
            raise RequestSerializationError(
                self._serializer.error_to_json(exc),
            ) from None

    def _validate_via_serializer(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run serializer validation for the combined model."""
        return cast(
            dict[str, Any],
            self._serializer.from_python(
                context,
                self._combined_model,
                strict=False,
            ),
        )

    def _bind_parsed(self, controller: Any, validated: dict[str, Any]) -> None:
        """Bind parsed values back to the controller instance."""
        for name, parsed_value in validated.items():
            setattr(controller, name, parsed_value)


def _build_type_map(  # noqa: WPS210
    controller_cls: type[Any],
    serializer: type[BaseSerializer],
) -> tuple[list[_ComponentSpec], dict[str, Any]]:
    """Build mapping name -> model and return specs and type_map."""
    specs: list[_ComponentSpec] = []
    type_map: dict[str, Any] = {}

    for component_cls, type_args in getattr(
        controller_cls,
        '_component_parsers',
        [],
    ):
        data_getter = component_cls.provide_context_data
        model = type_args[0]
        strict = getattr(component_cls, 'strict_validation', False)

        name = component_cls.context_name
        type_map[name] = model

        specs.append(
            _ComponentSpec(
                name=name,
                data_getter=data_getter,
                model=model,
                strict=strict,
            ),
        )
    return specs, type_map
