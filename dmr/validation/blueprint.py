import types
from typing import TYPE_CHECKING

from dmr.exceptions import EndpointMetadataError
from dmr.serializer import BaseSerializer
from dmr.validation.endpoint_metadata import validate_method_name

if TYPE_CHECKING:
    from dmr.controller import Blueprint


class BlueprintValidator:
    """
    Validate blueprint type definition.

    Validates:

    - Meta mixins
    - Components definition

    We don't validate complex stuff before creating a controller.
    """

    __slots__ = ()

    def __call__(self, blueprint: type['Blueprint[BaseSerializer]']) -> None:
        """Run the validation."""
        self._validate_meta_mixins(blueprint)
        self._validate_non_endpoints(blueprint)

    def _validate_meta_mixins(
        self,
        blueprint: type['Blueprint[BaseSerializer]'],
    ) -> None:
        from dmr.options_mixins import (  # noqa: PLC0415
            AsyncMetaMixin,
            MetaMixin,
        )

        if (
            issubclass(blueprint, MetaMixin)  # type: ignore[unreachable]
            and issubclass(blueprint, AsyncMetaMixin)  # type: ignore[unreachable]
        ):
            raise EndpointMetadataError(
                f'Use only one mixin, not both meta mixins in {blueprint!r}',
            )

    def _validate_non_endpoints(
        self,
        blueprint: type['Blueprint[BaseSerializer]'],
    ) -> None:
        for dir_item in dir(blueprint):  # noqa: WPS421
            method = getattr(blueprint, dir_item, None)
            if not isinstance(method, types.FunctionType):
                continue
            if getattr(method, '__dmr_payload__', None):
                validate_method_name(
                    method.__name__,
                    allowed_http_methods=blueprint.allowed_http_methods,
                )
