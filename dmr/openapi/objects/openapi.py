import dataclasses
from typing import TYPE_CHECKING, Protocol

from dmr.openapi.mappers.schema_normalization import (
    DumpedSchema,
    dump_schema,
)

if TYPE_CHECKING:
    from jsonschema_path.typing import Schema
    from openapi_spec_validator.validation.types import SpecValidatorType

    from dmr.openapi.objects.components import Components
    from dmr.openapi.objects.external_documentation import ExternalDocumentation
    from dmr.openapi.objects.info import Info
    from dmr.openapi.objects.path_item import PathItem
    from dmr.openapi.objects.paths import Paths
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.security_requirement import SecurityRequirement
    from dmr.openapi.objects.server import Server
    from dmr.openapi.objects.tag import Tag


class _ValidateSpecProto(Protocol):
    def __call__(
        self,
        spec: 'Schema',
        base_uri: str = '',
        cls: 'SpecValidatorType | None' = None,  # noqa: WPS117
    ) -> None: ...


_validate_spec: _ValidateSpecProto | None

try:
    # There's a mismatch of checks with mypyc and mypy,
    # so we use `unused-ignore` here:
    from openapi_spec_validator import (  # type: ignore[no-redef, unused-ignore]
        validate as _validate_spec,
    )
except ImportError:  # pragma: no cover
    _validate_spec = None


@dataclasses.dataclass(kw_only=True, slots=True)
class OpenAPI:
    """This is the root object of the OpenAPI document."""

    info: 'Info'
    openapi: str
    json_schema_dialect: str | None = None
    servers: list['Server'] | None = None
    paths: 'Paths | None' = None
    webhooks: dict[str, 'PathItem | Reference'] | None = None
    components: 'Components | None' = None
    security: list['SecurityRequirement'] | None = None
    tags: list['Tag'] | None = None
    external_docs: 'ExternalDocumentation | None' = None

    _validated: bool = dataclasses.field(
        default=False,
        init=False,
        repr=False,
        hash=False,
        compare=False,
    )

    def convert(self, *, skip_validation: bool = False) -> DumpedSchema:
        """
        Convert the object to OpenAPI schema dictionary.

        Runs validation if ``'django-modern-rest[openapi]'`` is installed
        and *skip_validation* is falsy.
        """
        spec = dump_schema(self)
        if (
            not skip_validation
            and not self._validated
            and _validate_spec is not None
        ):
            _validate_spec(spec)
            # Do not revalidate the same spec.
            self._validated = True
        return spec
