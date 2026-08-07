from typing import Any

try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:
    MsgspecSerializer = None

try:
    from dmr.plugins.pydantic import PydanticFastSerializer
except ImportError:
    PydanticFastSerializer = None


def load_openapi_part(unstructured: Any, model: type[Any]) -> Any:
    """Tries to load the given data of python primitives into a model."""
    if MsgspecSerializer is not None:
        return MsgspecSerializer.from_python(unstructured, model, strict=False)

    if PydanticFastSerializer is not None:
        return PydanticFastSerializer.from_python(
            unstructured,
            model,
            strict=False,
        )

    raise NotImplementedError(
        'No default serializers found, '
        'please override `Settings.openapi_schema_loader` value',
    )
