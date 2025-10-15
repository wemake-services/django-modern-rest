import abc
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, get_args

if TYPE_CHECKING:
    from django.http import HttpRequest

    from django_modern_rest.components import ComponentParserMixin
    from django_modern_rest.internal.json import FromJson

_ModelT = TypeVar('_ModelT')


class BaseSerializer:
    """Abstract base class for JSON serialization."""

    __slots__ = ()

    # API that needs to be set in subclasses:
    validation_error: ClassVar[type[Exception]]

    # API that have defaults:
    content_type: ClassVar[str] = 'application/json'

    @classmethod
    @abc.abstractmethod
    def to_json(cls, structure: Any) -> bytes:
        """Override this method to covert structured data to json bytestring."""
        raise NotImplementedError

    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        raise TypeError(
            f'Value {to_serialize} of type {type(to_serialize)} '
            'is not supported',
        )

    @classmethod
    @abc.abstractmethod
    def from_json(cls, buffer: 'FromJson') -> Any:
        raise NotImplementedError

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
    def deserialize_hook(
        cls,
        target_type: type[Any],
        to_deserialize: Any,
    ) -> Any:
        raise TypeError(
            f'Value {to_deserialize} of type {type(to_deserialize)} '
            f'is not supported for {target_type}',
        )

    @classmethod
    @abc.abstractmethod
    def create_combined_model(
        cls,
        component_specs: dict[str, type[Any]],
    ) -> type[Any]:
        """Create a single model that combines all component models."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def validate_combined(
        cls,
        combined_model: type[Any],
        component_data: dict[str, Any],
    ) -> Any:
        """Validate all data at once using combined model."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def error_to_json(cls, error: Exception) -> Any:
        """Serialize an exception to json the best way possible."""


class SerializerContext:
    """Context for collecting and parsing request components."""

    __slots__ = ('_combined_model', 'components', 'serializer')

    def __init__(
        self,
        components: Sequence['ComponentParserMixin'],
        serializer: type[BaseSerializer],
    ):
        self.components = components
        self.serializer = serializer

    def collect_and_parse(
        self,
        request: 'HttpRequest',
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Collect raw data from components and validate it all at once."""
        specs, raw_values = self._collect_components(request, *args, **kwargs)
        validated = self._validate_all(specs, raw_values)
        return {name: getattr(validated, name) for name in specs}

    def _collect_components(
        self,
        request: 'HttpRequest',
        *args: Any,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Extract specs and raw data from all components in single pass."""
        specs = {}
        raw_values = {}

        for component in self.components:
            type_args = get_args(component)
            if type_args:
                name = component._provide_context_name()  # noqa: SLF001
                specs[name] = type_args[0]
                raw_values[name] = component._provide_context_data(  # noqa: SLF001
                    request,
                    self.serializer,
                    type_args,
                    *args,
                    **kwargs,
                )

        return specs, raw_values

    def _validate_all(
        self,
        specs: dict[str, type[Any]],
        raw_values: dict[str, Any],
    ) -> Any:
        """Create combined model and validate all data at once."""
        combined_model = self.serializer.create_combined_model(specs)
        return self.serializer.validate_combined(combined_model, raw_values)
