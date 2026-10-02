from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dmr.openapi.objects.external_documentation import ExternalDocumentation


@dataclass(kw_only=True, slots=True)
class Tag:
    """
    Adds metadata to a single tag that is used by the `Operation` object.

    It is not mandatory to have a `Tag` object per tag defined in the
    `Operation` object instances.

    .. versionchanged:: 0.16.0
        Added ``summary``, ``parent``, and ``kind`` from OpenAPI 3.2.
        Added ``x_extensions`` for specification extensions.

    """

    name: str
    description: str | None = None
    external_docs: 'ExternalDocumentation | None' = None

    # OpenAPI 3.2+ fields:
    summary: str | None = None
    #: `name` of a tag this one is nested under, no circular references.
    parent: str | None = None
    #: Machine-readable tag category, like `nav`, `badge`, or `audience`.
    kind: str | None = None
    #: Specification extensions, keys must start with ``x-``.
    x_extensions: dict[str, Any] | None = None
