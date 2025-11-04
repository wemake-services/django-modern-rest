from typing import TYPE_CHECKING, get_args

from django_modern_rest.components import ComponentParser
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.types import infer_bases

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint


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
        self._validate_components(blueprint)

    def _validate_meta_mixins(
        self,
        blueprint: type['Blueprint[BaseSerializer]'],
    ) -> None:
        from django_modern_rest.options_mixins import (  # noqa: PLC0415
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

    def _validate_components(
        self,
        blueprint: type['Blueprint[BaseSerializer]'],
    ) -> None:
        possible_violations = infer_bases(
            blueprint,
            ComponentParser,
            use_origin=False,
        )
        for component_cls in possible_violations:
            if not get_args(component_cls):
                raise EndpointMetadataError(
                    f'Component {component_cls!r} in {blueprint!r} '
                    'must have 1 type argument, given 0',
                )
