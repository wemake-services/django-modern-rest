from typing import TYPE_CHECKING, Any, Final

from dmr.openapi.objects import Example, Schema
from dmr.types import EMPTY

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer

#: First OpenAPI version that deprecates `example` inside Schema Objects.
_JSON_SCHEMA_EXAMPLES_VERSION: Final = (3, 2)


def set_generated_example(
    schema: Schema,
    example: Any,
    context: 'OpenAPIContext',
) -> Schema:
    """
    Sets a generated *example* on the given *schema*, returns that *schema*.

    OpenAPI 3.2 deprecates the OAS ``example`` keyword inside Schema Objects
    in favour of the JSON Schema ``examples`` list. So, we only write
    ``example`` when targeting older OpenAPI versions.

    Generating examples can be disabled in settings, in that case *example*
    is ``None`` and we don't write anything at all.

    .. versionadded:: 0.16.0
    """
    if example is None:
        return schema
    if context.config.openapi_version_info[:2] < _JSON_SCHEMA_EXAMPLES_VERSION:
        schema.example = example
    else:
        schema.examples = [example]
    return schema


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
        if annotation is EMPTY:  # pragma: no cover
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
