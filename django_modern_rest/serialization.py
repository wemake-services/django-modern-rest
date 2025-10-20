import abc
import dataclasses
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, TypeVar

from django.http import HttpHeaders, HttpRequest
from typing_extensions import TypedDict

from django_modern_rest.exceptions import (
    RequestSerializationError,
    ResponseSerializationError,
)

if TYPE_CHECKING:
    from django_modern_rest.components import ComponentParser
    from django_modern_rest.controller import Controller
    from django_modern_rest.internal.json import FromJson
    from django_modern_rest.metadata import EndpointMetadata

_ModelT = TypeVar('_ModelT')
_ComponentParserSpec = dict[type['ComponentParser'], Any]
_TypeMapResult: TypeAlias = tuple[_ComponentParserSpec, dict[str, Any]]


class BaseSerializer:
    """Abstract base class for JSON serialization."""

    __slots__ = ()

    # API that needs to be set in subclasses:
    validation_error: ClassVar[type[Exception]]
    optimizer: ClassVar[type['BaseEndpointOptimizer']]
    response_parsing_error_model: ClassVar[Any]

    # API that have defaults:
    content_type: ClassVar[str] = 'application/json'

    @classmethod
    @abc.abstractmethod
    def serialize(cls, structure: Any) -> bytes:
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
    def deserialize(cls, buffer: 'FromJson') -> Any:
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
    def error_serialize(cls, error: Exception | str) -> Any:
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


@dataclasses.dataclass(slots=True)
class SerializerContext:
    """Parse and bind request components for a controller.

    This context collects raw data for all registered components, validates
    the combined payload in a single call using a cached TypedDict model,
    and then binds the parsed values back to the controller.
    """

    # Public API:
    strict_validation: ClassVar[bool] = False

    # Protected API:

    controller_cls: 'type[Controller[BaseSerializer]]'
    _specs: _ComponentParserSpec = dataclasses.field(init=False)
    _combined_model: Any = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        """Eagerly build context for a given controller and serializer."""
        specs, type_map = self._build_type_map(self.controller_cls)
        self._specs = specs

        # Name is not really important,
        # we use `@` to identify that it is generated:
        name_prefix = self.controller_cls.__qualname__
        combined_name = f'_{name_prefix}@ContextModel'

        self._combined_model = TypedDict(  # type: ignore[misc]
            combined_name,  # pyright: ignore[reportArgumentType]
            type_map,
            total=True,
        )

    def parse_and_bind(
        self,
        controller: 'Controller[BaseSerializer]',
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Collect, validate, and bind component data to the controller.

        Raises:
            serializer.validation_error: When provided data does not
                match the expected model.

        """
        context = self._collect_context(controller, request, *args, **kwargs)
        validated = self._validate_context(context)
        self._bind_parsed(controller, validated)

    def _build_type_map(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> _TypeMapResult:
        """Build mapping name -> model and return specs and type_map."""
        specs: _ComponentParserSpec = {}
        type_map: dict[str, Any] = {}
        parsers = controller_cls._component_parsers  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

        for component_cls, type_args in parsers:
            type_map[component_cls.context_name] = type_args[0]
            specs[component_cls] = type_args[0]
        return specs, type_map

    def _collect_context(
        self,
        controller: 'Controller[BaseSerializer]',
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Collect raw data for all components into a mapping."""
        context: dict[str, Any] = {}
        for component, submodel in self._specs.items():
            raw = component.provide_context_data(
                controller,  # type: ignore[arg-type]
                self.controller_cls.serializer,
                submodel,  # just the one for the exact key
                request,
                *args,
                **kwargs,
            )
            context[component.context_name] = raw
        return context

    def _validate_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate the combined payload using the cached TypedDict model."""
        serializer = self.controller_cls.serializer
        try:
            return serializer.from_python(  # type: ignore[no-any-return]
                context,
                self._combined_model,
                strict=self.strict_validation,
            )
        except serializer.validation_error as exc:
            raise RequestSerializationError(
                serializer.error_serialize(exc),
            ) from None

    def _bind_parsed(
        self,
        controller: 'Controller[BaseSerializer]',
        validated: dict[str, Any],
    ) -> None:
        """Bind parsed values back to the controller instance."""
        for name, parsed_value in validated.items():
            setattr(controller, name, parsed_value)
