from dataclasses import Field, fields, is_dataclass
from typing import Any, ClassVar, Protocol, TypeAlias, final

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.routing import Router

OpenAPISchema: TypeAlias = dict[str, Any]


class DataclassLike(Protocol):
    """Protocol for dataclasses."""

    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]  # noqa: WPS234


@final
class SchemaGenerator:
    """OpenAPI schema generator."""

    openapi_version: ClassVar[str] = '3.1.0'

    def __init__(self, config: OpenAPIConfig, router: Router) -> None:
        self.config = config
        self.router = router

    def to_schema(self) -> OpenAPISchema:
        return {
            'openapi': self.openapi_version,
            'info': _as_dict(self.config),
            'paths': {},  # TODO: implement paths generation
        }


def _as_dict(datacls: DataclassLike) -> dict[str, Any]:
    """
    Convert a dataclass to a dictionary.

    This function is used to convert a dataclass to a dictionary with aliases.
    """
    result_dict: dict[str, Any] = {}

    # TODO: adding yeild iteration over dataclass fields
    for field in fields(datacls):
        value = getattr(datacls, field.name)  # noqa: WPS110
        if value is None:
            continue

        key = field.metadata.get('alias', field.name)

        if is_dataclass(value):
            result_dict[key] = _as_dict(value)  # type: ignore[arg-type]
        else:
            result_dict[key] = value

    return result_dict
