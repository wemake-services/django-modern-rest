import decimal
import enum
from typing import Any

from dmr.openapi.objects.example import Example
from dmr.types import EmptyObj

try:
    from polyfactory.factories import DataclassFactory
except ImportError:  # pragma: no cover

    def generate_example(annotation: Any) -> Example | None:
        """Does nothing, since polyfactory is not installed."""

else:
    # The idea of generating examples and some parts of the implementation
    # is taken from the amazing Litestar project under MIT license:
    # https://github.com/litestar-org/litestar/blob/main/litestar/_openapi/schema_generation/examples.py
    from polyfactory.field_meta import FieldMeta

    class _ExampleFactory(DataclassFactory[Example]):
        __model__ = Example
        __random_seed__ = 10  # just a random number
        __check_model__ = False

    def generate_example(annotation: Any) -> Example | None:
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
            generated = _post_process_value(
                _ExampleFactory.get_field_value(
                    FieldMeta.from_type(annotation=annotation),
                ),
            )
        except Exception:  # pragma: no cover
            return None
        return Example(
            description='Generated example',
            value=generated,
        )


# pyright: reportUnknownVariableType=false
def _post_process_value(generated: Any) -> Any:  # noqa: C901
    if hasattr(generated, 'model_dump'):
        generated = generated.model_dump(mode='json')
    if isinstance(generated, (decimal.Decimal, float)):
        generated = round(generated, 2)
    if isinstance(generated, enum.Enum):  # pragma: no cover
        generated = generated.value

    # Must be at the bottom:
    if isinstance(generated, (list, set, frozenset, tuple)):
        generated = [_post_process_value(seq_item) for seq_item in generated]
    if isinstance(generated, dict):
        for dict_key, dict_value in generated.items():
            generated[dict_key] = _post_process_value(dict_value)
    return generated
