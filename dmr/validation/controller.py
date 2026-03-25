import types
from typing import TYPE_CHECKING

from dmr.exceptions import EndpointMetadataError
from dmr.serializer import BaseSerializer
from dmr.validation.endpoint_metadata import validate_method_name

if TYPE_CHECKING:
    from dmr.controller import Controller


class ControllerValidator:
    """Validates that controller is created correctly."""

    __slots__ = ()

    def __call__(
        self,
        controller: type['Controller[BaseSerializer]'],
    ) -> bool | None:
        """Run the validation."""
        is_async = self._validate_endpoints_color(controller)
        self._validate_error_handlers(controller, is_async=is_async)
        self._validate_meta_mixins(controller)
        self._validate_non_endpoints(controller)
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

    def _validate_error_handlers(
        self,
        controller: type['Controller[BaseSerializer]'],
        *,
        is_async: bool | None,
    ) -> None:
        if is_async is None:
            return

        handle_error_overridden = 'handle_error' in controller.__dict__
        handle_async_error_overridden = (
            'handle_async_error' in controller.__dict__
        )

        if is_async and handle_error_overridden:
            raise EndpointMetadataError(
                f'{controller!r} has async endpoints but overrides '
                '`handle_error` (sync handler). '
                'Use `handle_async_error` instead',
            )

        if not is_async and handle_async_error_overridden:
            raise EndpointMetadataError(
                f'{controller!r} has sync endpoints but overrides '
                '`handle_async_error` (async handler). '
                'Use `handle_error` instead',
            )

    def _validate_meta_mixins(
        self,
        controller: type['Controller[BaseSerializer]'],
    ) -> None:
        from dmr.options_mixins import (  # noqa: PLC0415
            AsyncMetaMixin,
            MetaMixin,
        )

        if (
            issubclass(controller, MetaMixin)
            and issubclass(controller, AsyncMetaMixin)  # type: ignore[unreachable]
        ):
            raise EndpointMetadataError(
                f'Use only one mixin, not both meta mixins in {controller!r}',
            )

    def _validate_non_endpoints(
        self,
        controller: type['Controller[BaseSerializer]'],
    ) -> None:
        for dir_item in dir(controller):  # noqa: WPS421
            method = getattr(controller, dir_item, None)
            if not isinstance(method, types.FunctionType):
                continue
            if getattr(method, '__dmr_payload__', None):
                validate_method_name(
                    method.__name__,
                    allowed_http_methods=controller.allowed_http_methods,
                )
