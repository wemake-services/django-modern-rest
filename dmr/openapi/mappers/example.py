from typing import TYPE_CHECKING, Annotated, Any, get_args, get_origin

from typing_extensions import Sentinel, override

from dmr.internal.types import EMPTY
from dmr.openapi.objects import Example, Schema

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer


def set_generated_example(schema: Schema, example: Any) -> Schema:
    """
    Sets a generated *example* on the given *schema*, returns that *schema*.

    We always use the JSON Schema ``examples`` list, never the OAS ``example``
    keyword: ``examples`` is valid in every OpenAPI version we support,
    while OpenAPI 3.2 deprecates ``example`` inside Schema Objects.

    When there's no example, *example* is :data:`~dmr.types.EMPTY`
    and we don't write anything at all. For example, when generating
    examples is disabled in settings. ``None`` is a valid example.

    .. versionadded:: 0.16.0
    """
    if example is not EMPTY:
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
    ) -> Any | Sentinel:
        """Does nothing, since polyfactory is not installed."""
        return EMPTY

else:
    # The idea of generating examples and some parts of the implementation
    # is taken from the amazing Litestar project under MIT license:
    # https://github.com/litestar-org/litestar/blob/main/litestar/_openapi/schema_generation/examples.py
    from polyfactory.field_meta import FieldMeta

    if TYPE_CHECKING:
        from polyfactory.factories.base import BaseFactory, BuildContext

        # Type checkers need to know what `super()` is in this mixin,
        # but in runtime it must not be a real factory:
        _MixinBase = BaseFactory[Any]
    else:
        _MixinBase = object

    class _FieldExamplesMixin(_MixinBase):
        """
        Uses hand-written examples of fields instead of random values.

        polyfactory only generates values from types and constraints.
        Only its ``pydantic`` factory can use field examples,
        and it does not do that by default. So, we do that ourselves
        for all models: ``pydantic``, ``msgspec``, dataclasses, and others.
        """

        __slots__ = ()

        @override
        @classmethod
        def get_field_value(
            cls,
            field_meta: FieldMeta,
            field_build_parameters: Any | None = None,
            build_context: 'BuildContext | None' = None,
        ) -> Any:
            """Returns the first hand-written example of a field, if any."""
            examples = cls._field_examples(field_meta)
            if examples:
                return examples[0]
            return super().get_field_value(
                field_meta,
                field_build_parameters=field_build_parameters,
                build_context=build_context,
            )

        @override
        @classmethod
        def _get_config(cls) -> dict[str, Any]:
            # polyfactory creates factories for nested models with this
            # config, `bases` makes them use this mixin too:
            return {
                **super()._get_config(),
                'bases': (_FieldExamplesMixin,),
            }

        @classmethod
        def _field_examples(cls, field_meta: FieldMeta) -> list[Any] | None:
            # `pydantic` factory keeps examples of fields in `FieldMeta`,
            # others keep them in `Annotated`, like `msgspec.Meta` does:
            examples = getattr(field_meta, 'examples', None)
            if examples or get_origin(field_meta.annotation) is not Annotated:
                return examples
            return next(
                (
                    metadata_examples
                    for metadata in get_args(field_meta.annotation)[1:]
                    if (
                        metadata_examples := getattr(metadata, 'examples', None)
                    )
                ),
                None,
            )

    class _ExampleFactory(_FieldExamplesMixin, DataclassFactory[Example]):
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
        if not isinstance(seed, Sentinel):
            _ExampleFactory.seed_random(seed)

    def generate_example(
        annotation: Any,
        serializer: type['BaseSerializer'],
    ) -> Any | Sentinel:
        """
        Generates examples based on the type annotation.

        Returns :data:`~dmr.types.EMPTY` when there's no example:
        when generating examples is disabled or has failed.

        .. versionchanged:: 0.16.0
            Returns :data:`~dmr.types.EMPTY` instead of ``None``
            when there's no example, because ``None`` is a valid example.

        """
        if annotation is EMPTY:  # pragma: no cover
            return EMPTY

        # Import cycle:
        from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

        if isinstance(
            resolve_setting(Settings.openapi_examples_seed),
            Sentinel,
        ):
            # Example generation is disabled in settings.
            return EMPTY

        try:  # noqa: WPS505
            return serializer.to_python(
                _ExampleFactory.get_field_value(
                    FieldMeta.from_type(annotation=annotation),
                ),
            )
        except Exception:  # pragma: no cover
            return EMPTY
