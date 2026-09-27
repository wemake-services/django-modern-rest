import datetime as dt
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

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

    #: Faker's defaults for dates and times end at the current time,
    #: so seeded examples would change with the clock. We use fixed bounds.
    _EXAMPLES_START: Final = dt.datetime.fromisoformat('2000-01-01T00:00Z')
    _EXAMPLES_END: Final = dt.datetime.fromisoformat('2026-01-01T00:00Z')
    _MAX_TIMEDELTA_SECONDS: Final = 7 * 24 * 60 * 60  # a week
    _EPOCH: Final = dt.datetime.fromisoformat('1970-01-01T00:00')

    class _ExampleFactory(DataclassFactory[Example]):
        # NOTE: don't set `__random_seed__` here, it only seeds the factory
        # once, when this class is created. `seed_examples` does the seeding,
        # because the seed comes from settings.
        __model__ = Example
        __check_model__ = True

        @override
        @classmethod
        def get_provider_map(cls) -> dict[Any, Callable[[], Any]]:
            """
            Generate dates and times in fixed bounds.

            Factories that are created for nested models
            get these providers too.
            """
            return {
                **super().get_provider_map(),
                dt.datetime: cls._random_datetime,
                dt.date: lambda: cls._random_datetime().date(),
                dt.time: lambda: cls._random_datetime().time(),
                dt.timedelta: lambda: dt.timedelta(
                    seconds=cls.__faker__.random_int(0, _MAX_TIMEDELTA_SECONDS),
                ),
            }

        @classmethod
        def _random_datetime(cls) -> dt.datetime:
            # We don't use Faker's date and time providers: on Windows
            # they only have second precision and they use the local timezone,
            # so the same seed gives different examples on different platforms.
            timestamp = cls.__faker__.random.uniform(
                _EXAMPLES_START.timestamp(),
                _EXAMPLES_END.timestamp(),
            )
            # Examples stay naive, like the Faker's ones:
            return _EPOCH + dt.timedelta(seconds=timestamp)

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
