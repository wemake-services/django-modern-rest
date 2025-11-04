from typing import (
    TYPE_CHECKING,
)

from typing_extensions import override

from django_modern_rest.exceptions import (
    EndpointMetadataError,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.validation.blueprint import BlueprintValidator

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint, Controller
    from django_modern_rest.endpoint import Endpoint


class ControllerValidator(BlueprintValidator):
    """
    Validates that controller is created correctly.

    Also validates possible composed blueprints.
    """

    __slots__ = ()

    @override
    def __call__(  # type: ignore[override]
        self,
        controller: type['Controller[BaseSerializer]'],
        /,
    ) -> bool:
        """Run the validation."""
        self._validate_blueprints(controller)
        self._validate_composed_endpoints(controller)
        return super().__call__(controller)

    def _validate_blueprints(
        self,
        controller: type['Controller[BaseSerializer]'],
    ) -> None:
        if not controller.blueprints:
            return

        serializer = controller.blueprints[0].serializer
        for blueprint in controller.blueprints:
            if serializer is not blueprint.serializer:
                raise EndpointMetadataError(
                    'Composing blueprints with different serializer types is '
                    f'not supported: {serializer} and {blueprint.serializer}',
                )

    def _validate_composed_endpoints(
        self,
        controller: type['Controller[BaseSerializer]'],
    ) -> None:
        canonical_methods = {
            canonical for canonical, _dsl in controller.existing_http_methods()
        }
        endpoints: dict[str, Endpoint] = {}
        for blueprint in controller.blueprints:
            self._validate_blueprint(
                blueprint,
                endpoints,
                controller,
                canonical_methods,
            )
            endpoints.update(blueprint.api_endpoints)

    def _validate_blueprint(
        self,
        blueprint: type['Blueprint[BaseSerializer]'],
        endpoints: dict[str, 'Endpoint'],
        controller: type['Controller[BaseSerializer]'],
        canonical_methods: set[str],
    ) -> None:
        blueprint_methods = blueprint.api_endpoints.keys()
        if not blueprint_methods:
            raise EndpointMetadataError(
                f'{blueprint} must have at least one endpoint to be composed',
            )
        method_intersection = blueprint_methods & canonical_methods
        if method_intersection:
            raise EndpointMetadataError(
                f'{blueprint} have {method_intersection!r} common methods '
                f'with {controller}',
            )
        method_intersection = endpoints.keys() & blueprint_methods
        if method_intersection:
            raise EndpointMetadataError(
                f'Blueprints have {method_intersection!r} common methods, '
                'while all endpoints must be unique',
            )
