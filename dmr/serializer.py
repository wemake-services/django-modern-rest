import abc
from collections import defaultdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, TypeVar

from django.http import FileResponse, HttpRequest, HttpResponseBase
from typing_extensions import TypedDict

from dmr.errors import ErrorDetail
from dmr.exceptions import (
    InternalServerError,
    RequestSerializationError,
    ValidationError,
)
from dmr.files import FileBody
from dmr.parsers import Parser, Raw
from dmr.renderers import Renderer

if TYPE_CHECKING:
    from dmr.components import ComponentParser
    from dmr.controller import Blueprint
    from dmr.endpoint import Endpoint
    from dmr.metadata import EndpointMetadata

_ModelT = TypeVar('_ModelT')
_ComponentParserSpec: TypeAlias = dict[type['ComponentParser'], Any]
_ContentTypeOverrides: TypeAlias = dict[str, dict[str, Any]]
_TypeMapResult: TypeAlias = tuple[
    _ComponentParserSpec,
    dict[str, Any],
    _ContentTypeOverrides,
]


class BaseSerializer:
    """
    Abstract base class for data serialization.

    Attributes:
        validation_error: Exception type that is used for validation errors.
            Required to be set in subclasses.
        optimizer: Endpoint optimizer.
            Type that pre-compiles / creates / caches models in import time.
            Required to be set in subclasses.

    """

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
        renderer: Renderer,
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
        if isinstance(to_serialize, (set, frozenset)):
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
        parser: Parser,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        """Convert json bytestring to structured data."""
        raise NotImplementedError

    @classmethod
    def deserialize_response(
        cls,
        response: HttpResponseBase,
        *,
        parser: Parser,
        request: HttpRequest,
    ) -> Any:
        """Deserialize non-HttpResponse response subclass."""
        return deserialize_response(response)

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


class DeserializableResponse:
    """
    Provides body content to be validated in our optional response validation.

    Abstract base class for custom responses
    that do not have content to be validated.
    For example, streaming responses might not have any content right now.

    But, we still need to validate something.
    """

    @abc.abstractmethod
    def deserializable_content(self) -> Any:
        """Provide response content for the validation."""
        raise NotImplementedError


def deserialize_response(response: HttpResponseBase) -> Any:
    """Deserialize complex response subtypes."""
    if isinstance(response, DeserializableResponse):
        return response.deserializable_content()
    if isinstance(response, FileResponse):
        return FileBody()
    raise InternalServerError(
        f'Unsupported response type {type(response)!r}',
    )


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


class SerializerContext:
    """Parse and bind request components for a controller.

    This context collects raw data for all registered components, validates
    the combined payload in a single call using a cached TypedDict model,
    and then binds the parsed values back to the controller.

    Attributes:
        strict_validation: Whether or not to validate payloads in strict mode.
            Strict mode in some serializers does
            not allow implicit type conversions.
            Defaults to ``None``. Which means that we decide
            on a per-field and then on a per-model basis.
    """

    # Public API:
    strict_validation: ClassVar[bool | None] = None

    # Protected API:
    _specs: _ComponentParserSpec
    _default_combined_model: Any
    _conditional_combined_models: dict[str, Any]

    __slots__ = (
        '_blueprint_cls',
        '_conditional_combined_models',
        '_default_combined_model',
        '_specs',
    )

    def __init__(
        self,
        blueprint_cls: type['Blueprint[BaseSerializer]'],
    ) -> None:
        """Eagerly build context for a given controller and serializer."""
        self._blueprint_cls = blueprint_cls
        specs, type_map, content_mapping = self._build_type_map(
            self._blueprint_cls,
        )
        self._specs = specs
        default_combined_model, conditional_combined_models = (
            self._build_combined_models(
                type_map,
                content_mapping,
            )
        )
        self._default_combined_model = default_combined_model
        self._conditional_combined_models = conditional_combined_models

    def __call__(
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
        validated = self._validate_context(context, blueprint)
        self._bind_parsed(blueprint, validated)

    def _build_type_map(  # noqa: WPS210
        self,
        blueprint_cls: type['Blueprint[BaseSerializer]'],
    ) -> _TypeMapResult:
        """
        Build the type parsing spec.

        Called during import-time.
        """
        specs: _ComponentParserSpec = {}
        type_map: dict[str, Any] = {}
        content_type_overrides: _ContentTypeOverrides = defaultdict(dict)

        for (
            component_cls,
            type_args,
        ) in blueprint_cls._component_parsers:  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            type_args = type_args[0] if len(type_args) == 1 else type_args
            type_map[component_cls.context_name] = type_args
            specs[component_cls] = type_args
            for content_type, model in component_cls.conditional_types(
                type_args,
            ).items():
                content_type_overrides[content_type].update({
                    component_cls.context_name: model,
                })
        return specs, type_map, content_type_overrides

    def _build_combined_models(
        self,
        type_map: dict[str, Any],
        content_type_overrides: _ContentTypeOverrides,
    ) -> tuple[Any, dict[str, Any]]:
        # Name is not really important,
        # we use `@` to identify that it is generated:
        name_prefix = self._blueprint_cls.__qualname__  # pyright: ignore[reportUnusedVariable]

        default_model = TypedDict(  # type: ignore[misc]
            f'_{name_prefix}@ContextModel',  # pyright: ignore[reportArgumentType]  # pyrefly: ignore[invalid-argument]
            type_map,
            total=True,
        )
        if not content_type_overrides:
            return default_model, {}

        content_mapping: dict[str, Any] = {}
        for content_type, overrides in content_type_overrides.items():  # pyright: ignore[reportUnusedVariable]
            content_mapping[content_type] = TypedDict(  # type: ignore[operator]
                f'_{name_prefix}@ContextModel#{content_type}',
                {
                    **type_map,  # pyright: ignore[reportGeneralTypeIssues]
                    **overrides,  # pyright: ignore[reportGeneralTypeIssues]
                },
                total=True,
            )
        return default_model, content_mapping

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
                field_model=submodel,  # just the exact field for the exact key
            )
            context[component.context_name] = raw
        return context

    def _validate_context(
        self,
        context: dict[str, Any],
        blueprint: 'Blueprint[BaseSerializer]',
    ) -> dict[str, Any]:
        """Validate the combined payload using the cached TypedDict model."""
        serializer = self._blueprint_cls.serializer
        content_type = blueprint.request.headers.get('Content-Type')
        model = (
            self._default_combined_model
            if content_type is None
            else self._conditional_combined_models.get(
                content_type,
                self._default_combined_model,
            )
        )
        try:
            return serializer.from_python(  # type: ignore[no-any-return]
                context,
                model,
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
