from dataclasses import dataclass
from typing import Literal, TypeAlias

#: Kind of an XML node that a `Schema` describes.
XMLNodeType: TypeAlias = Literal[
    'element',
    'attribute',
    'text',
    'cdata',
    'none',
]


@dataclass(kw_only=True, slots=True)
class XML:
    """
    A metadata object that allows for more fine-tuned XML model definitions.

    When using arrays, XML element names are not inferred
    (for singular/plural forms) and the name property `SHOULD` be used
    to add that information.

    .. versionchanged:: 0.16.0
        Added ``node_type`` from OpenAPI 3.2, it deprecates
        both ``attribute`` and ``wrapped``.
        Those two now default to ``None`` and are only dumped
        into the schema when they are set explicitly.

    """

    name: str | None = None
    namespace: str | None = None
    prefix: str | None = None

    #: Deprecated since OpenAPI 3.2, use ``node_type='attribute'`` instead.
    attribute: bool | None = None
    #: Deprecated since OpenAPI 3.2, use ``node_type='element'`` instead.
    wrapped: bool | None = None

    # OpenAPI 3.2+ fields:
    #: Mutually exclusive with `attribute` and `wrapped`.
    node_type: XMLNodeType | None = None
