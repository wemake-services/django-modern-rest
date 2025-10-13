from dataclasses import fields, is_dataclass
from typing import Any, ClassVar, TypeAlias, final

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.routing import Router

OpenAPISchema: TypeAlias = dict[str, Any]


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


def _as_dict(datacls: Any) -> dict[str, Any]:
    """
    Convert a dataclass to a dictionary.

    This function is used to convert a dataclass to a dictionary with aliases.
    """
    result_dict: dict[str, Any] = {}

    for field in fields(datacls):
        value = getattr(datacls, field.name)  # noqa: WPS110
        if value is None:
            continue

        key = field.metadata.get('alias', field.name)

        if is_dataclass(value):
            result_dict[key] = _as_dict(value)
        else:
            result_dict[key] = value

    return result_dict
