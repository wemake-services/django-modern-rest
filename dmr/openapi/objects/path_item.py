from dataclasses import dataclass
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from dmr.openapi.objects.operation import Operation
    from dmr.openapi.objects.parameter import Parameter
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.server import Server


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class PathItem:
    """
    Describes the operations available on a single path.

    A Path Item MAY be empty, due to ACL constraints.
    The path itself is still exposed to the documentation viewer but
    they will not know which operations and parameters are available.
    """

    ref: str | None = None
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
    servers: 'list[Server] | None' = None
    parameters: 'list[Parameter | Reference] | None' = None
