from collections import defaultdict
from collections.abc import Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias

from typing_extensions import TypedDict

from dmr.components import ComponentParser, ComponentParserBuilder
from dmr.exceptions import ValidationError

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


_ComponentParserSpec: TypeAlias = dict['ComponentParser', Any]
_ContentTypeOverrides: TypeAlias = dict[str, dict[str, Any]]
_TypeMapResult: TypeAlias = tuple[
    _ComponentParserSpec,
    dict[str, Any],
    _ContentTypeOverrides,
]


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
            on a per-field basis if it is set, if not then on a per-model basis.
    """

    # Public API:
    strict_validation: ClassVar[bool | None] = None
    component_builder_cls: ClassVar[type[ComponentParserBuilder]] = (
        ComponentParserBuilder
    )

    # Protected API:
    _specs: _ComponentParserSpec
    _default_combined_model: Any
    _conditional_combined_models: dict[str, Any]

    __slots__ = (
        '_conditional_combined_models',
        '_default_combined_model',
        '_specs',
        'component_parsers',
    )

    def __init__(
        self,
        func: Callable[..., Any],
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        """Eagerly build context for a given controller and serializer."""
        self.component_parsers = self.component_builder_cls(
            func,
            controller_cls,
        )()

        specs, type_map, content_mapping = self._build_type_map(func)
        self._specs = specs
        default_combined_model, conditional_combined_models = (
            self._build_combined_models(
                controller_cls,
                type_map,
                content_mapping,
            )
        )
        self._default_combined_model = default_combined_model
        self._conditional_combined_models = conditional_combined_models

    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> dict[str, Any]:
        """
        Collect, validate, and bind component data to the controller.

        Raises ``serializer.validation_error`` when provided
        data does not match the expected model.
        """
        if not self._specs:
            return {}

        context = self._collect_context(endpoint, controller)
        return self._validate_context(context, controller)

    def _build_type_map(  # noqa: WPS210
        self,
        func: Callable[..., Any],
    ) -> _TypeMapResult:
        """
        Build the type parsing spec.

        Called during import-time.
        """
        specs: _ComponentParserSpec = {}
        type_map: dict[str, Any] = {}
        content_type_overrides: _ContentTypeOverrides = defaultdict(dict)

        for component, model_type, model_meta in self.component_parsers:
            type_map[component.context_name] = model_type
            specs[component] = model_type
            for content_type, model in component.conditional_types(
                model_type,
                model_meta,
            ).items():
                content_type_overrides[content_type].update({
                    component.context_name: model,
                })
        return specs, type_map, content_type_overrides

    def _build_combined_models(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        type_map: dict[str, Any],
        content_type_overrides: _ContentTypeOverrides,
    ) -> tuple[Any, dict[str, Any]]:
        # Name is not really important,
        # we use `@` to identify that it is generated:
        name_prefix = controller_cls.__qualname__  # pyright: ignore[reportUnusedVariable]

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
        controller: 'Controller[BaseSerializer]',
    ) -> dict[str, Any]:
        """Collect raw data for all components into a mapping."""
        context: dict[str, Any] = {}
        for component, submodel in self._specs.items():
            raw = component.provide_context_data(
                endpoint,
                controller,
                field_model=submodel,  # just the exact field for the exact key
            )
            context[component.context_name] = raw
        return context

    def _validate_context(
        self,
        context: dict[str, Any],
        controller: 'Controller[BaseSerializer]',
    ) -> dict[str, Any]:
        """Validate the combined payload using the cached TypedDict model."""
        serializer = controller.serializer
        content_type = controller.request.headers.get('Content-Type')
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
