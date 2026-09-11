from typing import ClassVar, Final, final

import pydantic
from cryptography.fernet import Fernet

from dmr import Controller, Query
from dmr.pagination import CursorPaginated, CursorPaginator
from dmr.plugins.pydantic import PydanticFastSerializer
from server.apps.model_cursor.models import (  # type: ignore[import-not-found, unused-ignore]
    Entry,
)

FERNET_ENCODER: Final = Fernet(b'rrCDOaFu3QjLiRa8fwykCVp7nuPcKIbxnhZSiI_thBE=')


def custom_encoder(to_encode: str) -> str:
    """Encode a string using Fernet symmetric encryption."""
    return FERNET_ENCODER.encrypt(to_encode.encode()).decode(
        'utf-8',
    )


def custom_decoder(to_decode: str) -> str:
    """Decode a string using Fernet symmetric encryption."""
    return FERNET_ENCODER.decrypt(to_decode.encode()).decode(
        'utf-8',
    )


@final
class _PageQuery(pydantic.BaseModel):
    __dmr_cast_null__: ClassVar[frozenset[str]] = frozenset(('cursor',))

    cursor: str | None = None


class _EntrySchema(pydantic.BaseModel):
    rank: int
    name: str


class EntryController(Controller[PydanticFastSerializer]):
    """List entries using cursor-based pagination."""

    def get(
        self,
        parsed_query: Query[_PageQuery],
    ) -> CursorPaginated[_EntrySchema]:
        paginator = CursorPaginator(
            Entry.objects.all().order_by('rank', 'name'),
            per_page=2,
            cursor_encoder=custom_encoder,
            cursor_decoder=custom_decoder,
        )
        page = paginator.page(parsed_query.cursor)
        return CursorPaginated(
            next_cursor=page.next_cursor,
            per_page=paginator.per_page,
            page=[
                _EntrySchema.model_validate(entry, from_attributes=True)
                for entry in page.objects_list
            ],
        )


# run: {"controller": "EntryController", "method": "get", "url": "/api/entries/", "populate_db": true}  # noqa: ERA001, E501
