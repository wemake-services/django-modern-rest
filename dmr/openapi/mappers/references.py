import dataclasses
from collections.abc import Iterable, Iterator, Mapping, Sequence

from dmr.openapi.objects import Reference


def iter_references(node: object, schema_prefix: str) -> Iterator[str]:
    """
    Find names of all components referenced from an OpenAPI object.

    Walks any dataclass, list, or dict recursively
    and yields component names of all
    :class:`~dmr.openapi.objects.Reference` objects it finds,
    without the *schema_prefix*.

    .. versionadded:: 0.16.0
    """
    if isinstance(node, Reference):
        yield node.ref.removeprefix(schema_prefix)
    for child in _children(node):
        yield from iter_references(child, schema_prefix)


def _children(node: object) -> Iterable[object]:
    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        return (getattr(node, field.name) for field in dataclasses.fields(node))
    if isinstance(node, Mapping):
        return node.values()
    if isinstance(node, Sequence) and not isinstance(node, str):
        return node
    return ()
