from typing import ClassVar, Literal, TypeAlias, final

import pydantic

_AllowedOrderFields: TypeAlias = Literal[
    'rank',
    '-rank',
    'name',
    '-name',
    'created_at',
    '-created_at',
]


@final
class EntryModel(pydantic.BaseModel):
    rank: int
    name: str

    model_config = pydantic.ConfigDict(from_attributes=True)


@final
class CursorQuery(pydantic.BaseModel):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('order_by',))
    __dmr_cast_null__: ClassVar[frozenset[str]] = frozenset(('cursor',))

    cursor: str | None = None
    order_by: list[_AllowedOrderFields] = pydantic.Field(
        default=['rank', 'name'],
        min_length=1,
    )
    limit: int = pydantic.Field(
        default=2,
        gt=0,
        lt=100,
    )

    model_config = pydantic.ConfigDict(extra='forbid')
