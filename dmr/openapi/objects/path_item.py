from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Final

from dmr.internal.dataclass_aliases import Field

if TYPE_CHECKING:
    from dmr.openapi.objects.operation import Operation
    from dmr.openapi.objects.parameter import Parameter
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.server import Server


STANDARD_HTTP_METHODS: Final = frozenset((
    'get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace',
    'query',
))


@dataclass(kw_only=True, slots=True)
class PathItem:
    """
    Describes the operations available on a single path.

    A Path Item MAY be empty, due to ACL constraints.
    The path itself is still exposed to the documentation viewer but
    they will not know which operations and parameters are available.
    """

    ref: Annotated[str | None, Field(alias='$ref')] = None
    summary: str | None = None
    description: str | None = None
    get: 'Operation | None' = None
    put: 'Operation | None' = None
    post: 'Operation | None' = None
    delete: 'Operation | None' = None
    options: 'Operation | None' = None
    head: 'Operation | None' = None
    patch: 'Operation | None' = None
    trace: 'Operation | None' = None
    query: 'Operation | None' = None
    servers: list['Server'] | None = None
    parameters: list['Parameter | Reference'] | None = None
    additional_operations: dict[str, 'Operation'] | None = None
