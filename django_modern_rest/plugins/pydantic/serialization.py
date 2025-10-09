from functools import lru_cache
from typing import Any, TypeVar

import pydantic
from django.conf import settings

from django_modern_rest.settings import DMR_SETTINGS

_ModelT = TypeVar('_ModelT', bound=pydantic.BaseModel)


def model_dump_json(
    model: pydantic.BaseModel,
    # TODO: support typed per-thing configuration
    # dump_kwargs: DumpKwargsTypedDict,
    dump_kwargs: dict[str, Any],
) -> str:
    """Dumps *model* respecting all configuration: global and class levels."""
    kwargs = _model_dump_kwargs()
    kwargs.update(dump_kwargs)
    return model.model_dump_json(**kwargs)


def model_validate(
    model_type: type[_ModelT],
    to_validate: dict[str, Any],
    # TODO: support typed per-thing configuration
    # validate_kwargs: ValidateKwargsTypedDict,
    validate_kwargs: dict[str, Any],
) -> _ModelT:
    """Loads *model* respecting all configuration: global and class levels."""
    kwargs = _model_validate_kwargs()
    kwargs.update(validate_kwargs)
    return model_type.model_validate(to_validate, **kwargs)


@lru_cache
def _model_dump_kwargs() -> dict[str, Any]:
    return (  # type: ignore[no-any-return]
        getattr(settings, DMR_SETTINGS, {})
        .get('pydantic', {})
        # TODO: document defaults
        .get(
            'model_dump_kwargs',
            {'mode': 'json', 'by_alias': True, 'by_name': False},
        )
    )


@lru_cache
def _model_validate_kwargs() -> dict[str, Any]:
    return (  # type: ignore[no-any-return]
        getattr(settings, DMR_SETTINGS, {})
        .get('pydantic', {})
        .get('model_validate_kwargs', {'by_alias': True, 'by_name': False})
    )
