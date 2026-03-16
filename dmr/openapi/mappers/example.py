from typing import TYPE_CHECKING, Any

from dmr.openapi.objects import Example
from dmr.types import EmptyObj

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer

try:
    from polyfactory.factories import DataclassFactory
except ImportError:  # pragma: no cover

    def generate_example(
        annotation: Any,
        serializer: type['BaseSerializer'],
    ) -> Any | None:
        """Does nothing, since polyfactory is not installed."""

else:
    # The idea of generating examples and some parts of the implementation
    # is taken from the amazing Litestar project under MIT license:
    # https://github.com/litestar-org/litestar/blob/main/litestar/_openapi/schema_generation/examples.py
    from polyfactory.field_meta import FieldMeta

    class _ExampleFactory(DataclassFactory[Example]):
        __model__ = Example
        __random_seed__ = 10  # just a random number
        __check_model__ = True

    def generate_example(
        annotation: Any,
        serializer: type['BaseSerializer'],
    ) -> Any | None:
        """Generates examples based on the type annotation."""
        if annotation is EmptyObj:  # pragma: no cover
            return None

        # Import cycle:
        from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

        seed = resolve_setting(Settings.openapi_examples_seed)
        if seed is None:
            # Example generation is disabled in settings.
            return None

        if _ExampleFactory.__random_seed__ != seed:  # pragma: no cover
            # Reseed the factory, if it is required.
            _ExampleFactory.seed_random(seed)

        try:  # noqa: WPS505
            return serializer.to_python(
                _ExampleFactory.get_field_value(
                    FieldMeta.from_type(annotation=annotation),
                ),
            )
        except Exception:  # pragma: no cover
            return None
