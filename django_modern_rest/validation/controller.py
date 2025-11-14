from collections.abc import Set
from typing import TYPE_CHECKING

from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.serialization import BaseSerializer

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint, Controller


class ControllerValidator:
    """
    Validates that controller is created correctly.

    Also validates possible composed blueprints.
    """

    __slots__ = ()

    def __call__(
        self,
        controller: type['Controller[BaseSerializer]'],
    ) -> bool | None:
        """Run the validation."""
        is_async = self._validate_endpoints_color(controller)
        self._validate_error_handlers(controller, is_async=is_async)
        self._validate_blueprints(controller, is_async=is_async)
        return is_async

    def _validate_endpoints_color(
        self,
        controller: type['Controller[BaseSerializer]'],
    ) -> bool | None:
        """What colors are our endpoints?"""
        if not controller.api_endpoints:
            return None

        is_async = controller.api_endpoints[
            next(iter(controller.api_endpoints.keys()))
        ].is_async
        if any(
            endpoint.is_async is not is_async
            for endpoint in controller.api_endpoints.values()
        ):
            # The same error message that django has.
            raise EndpointMetadataError(
                'HTTP handlers must either be all sync or all async, '
                f'{controller!r} has mixed sync and async state',
            )
        return is_async

    def _validate_blueprints(
        self,
        controller: type['Controller[BaseSerializer]'],
        *,
        is_async: bool | None,
    ) -> None:
        if not controller.blueprints:
            return

        if controller._component_parsers:  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            raise EndpointMetadataError(
                f'{controller=} has blueprints but also has component parsers. '
                'Controllers with blueprints must not have any parsing. '
                'If you need parsed data, put parsing into blueprints instead.',
            )

        controller_methods = controller._existing_http_methods.keys()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        endpoints: set[str] = set()
        for blueprint in controller.blueprints:
            if controller.serializer is not blueprint.serializer:
                raise EndpointMetadataError(
                    'Composing blueprints with different serializer types '
                    f'is not supported: {controller.serializer} '
                    f'and {blueprint.serializer}',
                )

            # `is_async` can't be `None` now, since we have at least one
            # correct blueprint.
            assert is_async is not None  # noqa: S101
            self._validate_error_handlers(blueprint, is_async=is_async)

            endpoints.update(
                self._check_blueprint_methods(
                    blueprint,
                    endpoints,
                    controller,
                    controller_methods,
                ),
            )

    def _check_blueprint_methods(
        self,
        blueprint: type['Blueprint[BaseSerializer]'],
        endpoints: set[str],
        controller: type['Controller[BaseSerializer]'],
        controller_methods: Set[str],
    ) -> Set[str]:
        blueprint_methods = blueprint._existing_http_methods.keys()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        if not blueprint_methods:
            raise EndpointMetadataError(
                f'{blueprint} must have at least one endpoint to be composed',
            )
        method_intersection = blueprint_methods & controller_methods
        if method_intersection:
            raise EndpointMetadataError(
                f'{blueprint} have {method_intersection!r} common methods '
                f'with {controller}',
            )
        method_intersection = endpoints & blueprint_methods
        if method_intersection:
            raise EndpointMetadataError(
                f'Blueprints have {method_intersection!r} common methods, '
                'while all endpoints must be unique',
            )
        return blueprint_methods

    def _validate_error_handlers(
        self,
        blueprint: type['Blueprint[BaseSerializer]'],
        *,
        is_async: bool | None,
    ) -> None:
        if is_async is None:
            return

        handle_error_overridden = 'handle_error' in blueprint.__dict__
        handle_async_error_overridden = (
            'handle_async_error' in blueprint.__dict__
        )

        if is_async and handle_error_overridden:
            raise EndpointMetadataError(
                f'{blueprint!r} has async endpoints but overrides '
                '`handle_error` (sync handler). '
                'Use `handle_async_error` instead',
            )

        if not is_async and handle_async_error_overridden:
            raise EndpointMetadataError(
                f'{blueprint!r} has sync endpoints but overrides '
                '`handle_async_error` (async handler). '
                'Use `handle_error` instead',
            )
