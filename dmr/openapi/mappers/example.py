from typing import TYPE_CHECKING, Any

from dmr.openapi.objects import Example, Schema
from dmr.types import EMPTY

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer


def set_generated_example(schema: Schema, example: Any) -> Schema:
    """
    Sets a generated *example* on the given *schema*, returns that *schema*.

    We always use the JSON Schema ``examples`` list, never the OAS ``example``
    keyword: ``examples`` is valid in every OpenAPI version we support,
    while OpenAPI 3.2 deprecates ``example`` inside Schema Objects.

    Generating examples can be disabled in settings, in that case *example*
    is ``None`` and we don't write anything at all.

    .. versionadded:: 0.16.0
    """
    if example is not None:
        schema.examples = [example]
    return schema


try:
    from polyfactory.factories import DataclassFactory
except ImportError:  # pragma: no cover

    def seed_example_factory() -> None:
        """Does nothing, since polyfactory is not installed."""

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
        # NOTE: don't set `__random_seed__` here, it only seeds the factory
        # once, when this class is created. `seed_examples` does the seeding,
        # because the seed comes from settings.
        __model__ = Example
        __check_model__ = True

    def seed_example_factory() -> None:
        """
        Seed the example factory from settings.

        Call it once per OpenAPI schema build, which is what
        :meth:`dmr.openapi.OpenAPIContext.seed_examples` does.

        All examples of a single schema come from one seeded random stream,
        which is what makes them differ from each other. Seeding again
        before every example would restart that stream and give every
        schema of the same type the same value.

        Seeding per build also keeps a schema reproducible on its own:
        the factory is shared state, so without this the values would
        depend on how many examples were generated before.

        .. versionadded:: 0.16.0
        """
        # Import cycle:
        from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

        seed = resolve_setting(Settings.openapi_examples_seed)
        if seed is not None:
            _ExampleFactory.seed_random(seed)

    def generate_example(
        annotation: Any,
        serializer: type['BaseSerializer'],
    ) -> Any | None:
        """Generates examples based on the type annotation."""
        if annotation is EMPTY:  # pragma: no cover
            return None

        # Import cycle:
        from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

        if resolve_setting(Settings.openapi_examples_seed) is None:
            # Example generation is disabled in settings.
            return None

        try:  # noqa: WPS505
            return serializer.to_python(
                _ExampleFactory.get_field_value(
                    FieldMeta.from_type(annotation=annotation),
                ),
            )
        except Exception:  # pragma: no cover
            return None
