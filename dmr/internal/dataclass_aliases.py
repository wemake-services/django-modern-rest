import dataclasses
from typing import Protocol, final


class _FieldLike(Protocol):
    alias: str

    def __init__(self, alias: str) -> None: ...


#: We either import a field from pydantic, or use our own fallback.
Field: type[_FieldLike]  # pyright: ignore[reportRedeclaration]

#: Type of the field we create. In pyndatic `Field()` is a function.
FieldInfo: type[_FieldLike]

try:  # noqa: WPS229
    # mypy and mypyc raise different errors here, `unused-ignore` saves the day:
    from pydantic import Field  # type: ignore[assignment, no-redef, unused-ignore]
    from pydantic.fields import FieldInfo  # type: ignore[assignment, no-redef, unused-ignore]
except ImportError:

    @final
    @dataclasses.dataclass
    class Field:  # type: ignore[no-redef]
        """
        Our own metadata type for the field aliases.

        Used when pydantic is not installed for the schema dumping.
        """

        alias: str

    FieldInfo = Field
