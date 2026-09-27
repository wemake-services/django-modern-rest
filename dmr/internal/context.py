from collections import defaultdict
from collections.abc import Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias

from dmr.components import ComponentParser, ComponentParserBuilder
from dmr.exceptions import ValidationError
from dmr.serializer import ContextField, ContextModel

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

_ContextFields: TypeAlias = dict[str, ContextField]
_ContentTypeOverrides: TypeAlias = dict[str, dict[str, Any]]
#: Component name, component, its model, and its default.
_CollectPlan: TypeAlias = tuple[tuple[str, ComponentParser, Any, Any], ...]


class SerializerContext:
    """
    Parse and bind request components for a controller.

    This context collects raw data for all registered components, validates
    the combined payload in a single call using a cached model
    that the serializer builds, and then binds the parsed values
    back to the controller.

    Components with default values return them
    when a request has no data for them, so the endpoint
    receives their real python defaults.

    Attributes:
        strict_validation: Whether or not to validate payloads in strict mode.
            Strict mode in some serializers does
            not allow implicit type conversions.
            Defaults to ``None``, which means that we decide
            on a per-field basis if it is set, if not then on a per-model basis.

    .. versionchanged:: 0.16.0
        Models are now built by ``serializer.build_context_model``,
        defaults of component parameters are now supported.

    """

    # Public API:
    strict_validation: ClassVar[bool | None] = None

    #: Type that will be used  to build parsing components.
    component_builder_cls: ClassVar[type[ComponentParserBuilder]] = (
        ComponentParserBuilder
    )

    # Protected API:
    _collect_plan: _CollectPlan
    _default_model: ContextModel
    _conditional_models: dict[str, ContextModel]

    __slots__ = (
        '_collect_plan',
        '_conditional_models',
        '_default_model',
        'component_parsers',
    )

    def __init__(
        self,
        func: Callable[..., Any],
        controller_cls: type['Controller[BaseSerializer]'],
        type_annotations: dict[str, Any],
    ) -> None:
        """Eagerly build context for a given controller and serializer."""
        # Build component parsers:
        self.component_parsers = self.component_builder_cls(
            func,
            controller_cls,
        )(type_annotations)

        # Build models and conditional models:
        fields, content_type_overrides = self._build_fields()
        default_model, conditional_models = self._build_models(
            controller_cls,
            fields,
            content_type_overrides,
        )
        self._default_model = default_model
        self._conditional_models = conditional_models

        # Prepare values to collect the context from:
        self._collect_plan = tuple(
            (
                spec.parser.context_name,
                spec.parser,
                spec.model,
                spec.default,
            )
            for spec in self.component_parsers
        )

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
        if not self._collect_plan:
            return {}

        context = self._collect_context(endpoint, controller)
        return self._validate_context(context, controller)

    # Import time methods:

    def _build_fields(
        self,
    ) -> tuple[_ContextFields, _ContentTypeOverrides]:
        """
        Build the type parsing spec.

        Called during import-time.
        """
        fields: _ContextFields = {}
        content_type_overrides: _ContentTypeOverrides = defaultdict(dict)

        for spec in self.component_parsers:
            fields[spec.parser.context_name] = ContextField(
                spec.model,
                spec.default,
            )
            for content_type, model in spec.parser.conditional_types(
                spec.model,
                spec.model_meta,
            ).items():
                content_type_overrides[content_type].update({
                    spec.parser.context_name: model,
                })
        return fields, content_type_overrides

    def _build_models(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        fields: _ContextFields,
        content_type_overrides: _ContentTypeOverrides,
    ) -> tuple[ContextModel, dict[str, ContextModel]]:
        # Name is not really important,
        # we use `@` to identify that it is generated:
        name_prefix = controller_cls.__qualname__
        default_model = controller_cls.serializer.build_context_model(
            f'_{name_prefix}@ContextModel',
            fields,
        )
        return default_model, {
            content_type: controller_cls.serializer.build_context_model(
                f'_{name_prefix}@ContextModel_{content_type}',
                self._override_fields(fields, overrides),
            )
            for content_type, overrides in content_type_overrides.items()
        }

    def _override_fields(
        self,
        fields: _ContextFields,
        overrides: dict[str, Any],
    ) -> _ContextFields:
        """Replace annotations of some fields, but keep their defaults."""
        return {
            **fields,
            **{
                field_name: ContextField(model, fields[field_name].default)
                for field_name, model in overrides.items()
            },
        }

    # Runtime methods:

    def _collect_context(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> dict[str, Any]:
        """Collect raw data for all components into a mapping."""
        context: dict[str, Any] = {}
        for context_name, component, submodel, default in self._collect_plan:
            context[context_name] = component.provide_context_data(
                endpoint,
                controller,
                field_model=submodel,  # just the exact field for the exact key
                default=default,
            )
        return context

    def _validate_context(
        self,
        context: dict[str, Any],
        controller: 'Controller[BaseSerializer]',
    ) -> dict[str, Any]:
        """Validate the combined payload using the cached model."""
        serializer = controller.serializer
        context_model = self._default_model
        if self._conditional_models:
            context_model = self._conditional_models.get(  # pyrefly: ignore[no-matching-overload]  # pyright: ignore[reportUnknownVariableType]
                controller.request.content_type,  # type: ignore[arg-type]
                context_model,
            )
        try:
            parsed = serializer.from_python(
                context,
                context_model.model,  # pyright: ignore[reportUnknownMemberType]
                strict=self.strict_validation,
            )
        except serializer.validation_error as exc:
            raise ValidationError(
                serializer.serialize_validation_error(exc),
                status_code=HTTPStatus.BAD_REQUEST,
            ) from None
        if context_model.to_kwargs is None:  # pyright: ignore[reportUnknownMemberType]
            return parsed  # type: ignore[no-any-return]
        return context_model.to_kwargs(parsed)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
