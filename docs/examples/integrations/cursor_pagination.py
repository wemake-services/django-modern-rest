from typing import Annotated, ClassVar, final

import pydantic
from annotated_types import Gt, Lt

from dmr import Controller, Query
from dmr.pagination import CursorPaginated, CursorPaginator
from dmr.plugins.pydantic import PydanticFastSerializer
from server.apps.model_cursor.models import (  # type: ignore[import-not-found, unused-ignore]
    Entry,
)


@final
class _PageQuery(pydantic.BaseModel):
    __dmr_cast_null__: ClassVar[frozenset[str]] = frozenset(('cursor',))

    cursor: str | None = None
    page_size: Annotated[int, Gt(0), Lt(100)] = 2


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
            parsed_query.page_size,
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
# run: {"controller": "EntryController", "method": "get", "url": "/api/entries/", "query": "?cursor=MnwtfGF8LXwy", "populate_db": true, "curl_args": ["-D", "-"], "assert-error-text": "cannot be decoded", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "EntryController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
