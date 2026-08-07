from dataclasses import dataclass, field


@dataclass(kw_only=True, slots=True)
class Reference:
    """
    A simple object to allow referencing other components in the document.

    The `$ref` string value contains a URI RFC3986, which identifies
    the location of the value being referenced.
    """

    ref: str = field(metadata={'alias': '$ref'})
    summary: str | None = None
    description: str | None = None
