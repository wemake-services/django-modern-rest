import abc
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, TypeVar

from typing_extensions import TypedDict

from django_modern_rest.errors import ErrorDetail
from django_modern_rest.exceptions import (
    InternalServerError,
    RequestSerializationError,
    ValidationError,
)
from django_modern_rest.parsers import Parser, Raw
from django_modern_rest.renderers import Renderer

if TYPE_CHECKING:
    from django_modern_rest.components import ComponentParser
    from django_modern_rest.controller import Blueprint
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.metadata import EndpointMetadata

_ModelT = TypeVar('_ModelT')
_ComponentParserSpec = dict[type['ComponentParser'], Any]
_TypeMapResult: TypeAlias = tuple[_ComponentParserSpec, dict[str, Any]]


class BaseSerializer:
    """Abstract base class for data serialization."""

    __slots__ = ()

    # API that needs to be set in subclasses:
    validation_error: ClassVar[type[Exception]]
    optimizer: ClassVar[type['BaseEndpointOptimizer']]

    @classmethod
    @abc.abstractmethod
    def serialize(
        cls,
        structure: Any,
        *,
        renderer_cls: type[Renderer],
    ) -> bytes:
        """Convert structured data to json bytestring."""
        raise NotImplementedError

    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        """
        Customize how some objects are serialized into json.

        Only add types that are common for all potential plugins here.
        Should be called inside :meth:`serialize`.
        """
        if isinstance(to_serialize, (set, frozenset)):  # pragma: no cover
            # This is impossible to reach with `msgspec`, but is needed
            # for raw `json` serialization.
            return list(to_serialize)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
        raise InternalServerError(
            f'Value {to_serialize} of type {type(to_serialize)} '
            'is not supported',
        )

    @classmethod
    @abc.abstractmethod
    def deserialize(
        cls,
        buffer: Raw,
        *,
        parser_cls: type[Parser],
    ) -> Any:
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
        Should be called inside :meth:`deserialize`.
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
        strict: bool | None,
    ) -> Any:
        """
        Parse *unstructured* data from python primitives into *model*.

        Raises ``cls.validation_error`` when something cannot be parsed.

        Args:
            unstructured: Python objects to be parsed / validated.
            model: Python type to serve as a model.
                Can be any type hints that user can theoretically supply.
                Depends on the serialization plugin.
            strict: Whether we use more strict validation rules.
                For example, it is fine for a request validation
                to be less strict in some cases and allow type coercition.
                But, response types need to be strongly validated.

        Returns:
            Structured and validated data.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def serialize_validation_error(
        cls,
        exc: Exception,
    ) -> list[ErrorDetail]:
        """
        Convert specific serializer's validation errors into simple python data.

        Args:
            exc: A serialization exception to be serialized into simpler type.
                For example, pydantic has
                a complex :exc:`pydantic_core.ValidationError` type.
                That can't be converted to a simpler error message easily.

        Returns:
            Simple python object - exception converted to json.
        """
        raise NotImplementedError


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


# TODO: make generic on `blueprint_cls`?
class SerializerContext:
    """Parse and bind request components for a controller.

    This context collects raw data for all registered components, validates
    the combined payload in a single call using a cached TypedDict model,
    and then binds the parsed values back to the controller.
    """

    # Public API:
    strict_validation: ClassVar[bool | None] = None

    # Protected API:
    _specs: _ComponentParserSpec
    _combined_model: Any

    __slots__ = ('_blueprint_cls', '_combined_model', '_specs')

    def __init__(
        self,
        blueprint_cls: type['Blueprint[BaseSerializer]'],
    ) -> None:
        """Eagerly build context for a given controller and serializer."""
        self._blueprint_cls = blueprint_cls
        specs, type_map = _build_type_map(self._blueprint_cls)
        self._specs = specs

        # Name is not really important,
        # we use `@` to identify that it is generated:
        name_prefix = self._blueprint_cls.__qualname__
        combined_name = f'_{name_prefix}@ContextModel'

        self._combined_model = TypedDict(  # type: ignore[misc]
            combined_name,  # pyright: ignore[reportArgumentType]
            type_map,
            total=True,
        )

    def parse_and_bind(
        self,
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
    ) -> None:
        """
        Collect, validate, and bind component data to the controller.

        Raises:
            serializer.validation_error: When provided data does not
                match the expected model.

        """
        if not self._specs:
            return

        context = self._collect_context(endpoint, blueprint)
        validated = self._validate_context(context)
        self._bind_parsed(blueprint, validated)

    def _collect_context(
        self,
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
    ) -> dict[str, Any]:
        """Collect raw data for all components into a mapping."""
        context: dict[str, Any] = {}
        for component, submodel in self._specs.items():
            raw = component.provide_context_data(
                endpoint,
                blueprint,
                field_model=submodel,  # just the one for the exact key
                combined_model=self._combined_model,
            )
            context[component.context_name] = raw
        return context

    def _validate_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate the combined payload using the cached TypedDict model."""
        serializer = self._blueprint_cls.serializer
        try:
            return serializer.from_python(  # type: ignore[no-any-return]
                context,
                self._combined_model,
                strict=self.strict_validation,
            )
        except serializer.validation_error as exc:
            raise ValidationError(
                serializer.serialize_validation_error(exc),
                status_code=HTTPStatus.BAD_REQUEST,
            ) from None

    def _bind_parsed(
        self,
        blueprint: 'Blueprint[BaseSerializer]',
        validated: dict[str, Any],
    ) -> None:
        """Bind parsed values back to the blueprint instance."""
        for name, parsed_value in validated.items():
            setattr(blueprint, name, parsed_value)


def _build_type_map(
    blueprint_cls: type['Blueprint[BaseSerializer]'],
) -> _TypeMapResult:
    """
    Build the type parsing spec.

    Called during import-time.
    """
    specs: _ComponentParserSpec = {}
    type_map: dict[str, Any] = {}
    parsers = blueprint_cls._component_parsers  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

    for component_cls, type_args in parsers:
        type_map[component_cls.context_name] = type_args[0]
        specs[component_cls] = type_args[0]
    return specs, type_map
