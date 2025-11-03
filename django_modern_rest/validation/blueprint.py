from typing import (
    TYPE_CHECKING,
    get_args,
)

from django_modern_rest.components import ComponentParser
from django_modern_rest.exceptions import (
    EndpointMetadataError,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import (
    infer_bases,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint


class BlueprintValidator:
    """
    Validate blueprint type definition.

    Validates:
    - Async vs sync blueprints
    - Components definition
    """

    __slots__ = ()

    def __call__(self, blueprint: 'type[Blueprint[BaseSerializer]]', /) -> bool:
        """Run the validation."""
        self._validate_components(blueprint)
        is_async = self._validate_endpoints(blueprint)
        self._validate_meta_mixins(blueprint, is_async=is_async)
        self._validate_error_handlers(blueprint, is_async=is_async)
        return is_async

    def _validate_meta_mixins(
        self,
        blueprint: 'type[Blueprint[BaseSerializer]]',
        *,
        is_async: bool = False,
    ) -> None:
        from django_modern_rest.options_mixins import (  # noqa: PLC0415
            AsyncMetaMixin,
            MetaMixin,
        )

        if (
            issubclass(blueprint, MetaMixin)  # type: ignore[unreachable]
            and issubclass(blueprint, AsyncMetaMixin)  # type: ignore[unreachable]
        ):
            suggestion = (  # type: ignore[unreachable]
                'AsyncMetaMixin' if is_async else 'MetaMixin'
            )
            raise EndpointMetadataError(
                f'Use only {suggestion!r}, '
                f'not both meta mixins in {blueprint!r}',
            )

    def _validate_components(
        self,
        blueprint: 'type[Blueprint[BaseSerializer]]',
    ) -> None:
        possible_violations = infer_bases(
            blueprint,
            ComponentParser,
            use_origin=False,
        )
        for component_cls in possible_violations:
            if not get_args(component_cls):
                raise EndpointMetadataError(
                    f'Component {component_cls} in {blueprint} '
                    'must have 1 type argument, given 0',
                )

    def _validate_endpoints(
        self,
        blueprint: 'type[Blueprint[BaseSerializer]]',
    ) -> bool:
        if not blueprint.api_endpoints:
            return False
        is_async = blueprint.api_endpoints[
            next(iter(blueprint.api_endpoints.keys()))
        ].is_async
        if any(
            endpoint.is_async is not is_async
            for endpoint in blueprint.api_endpoints.values()
        ):
            # The same error message that django has.
            raise EndpointMetadataError(
                f'{blueprint!r} HTTP handlers must either '
                'be all sync or all async',
            )
        return is_async

    def _validate_error_handlers(
        self,
        blueprint: 'type[Blueprint[BaseSerializer]]',
        *,
        is_async: bool,
    ) -> None:
        if not blueprint.api_endpoints:
            return

        handle_error_overridden = 'handle_error' in blueprint.__dict__
        handle_async_error_overridden = (
            'handle_async_error' in blueprint.__dict__
        )

        if is_async and handle_error_overridden:
            raise EndpointMetadataError(
                f'{blueprint!r} has async endpoints but overrides '
                '`handle_error` (sync handler). '
                'Use `handle_async_error` instead for async endpoints.',
            )

        if not is_async and handle_async_error_overridden:
            raise EndpointMetadataError(
                f'{blueprint!r} has sync endpoints but overrides '
                '`handle_async_error` (async handler). '
                'Use `handle_error` instead for sync endpoints.',
            )
