from http import HTTPStatus
from typing import final, override

from django.http import HttpResponse

from dmr import Controller, Query
from dmr.endpoint import Endpoint
from dmr.pagination import CursorPaginated, CursorPaginator
from dmr.pagination.cursor import InvalidCursorError
from dmr.plugins.pydantic.serializer import PydanticFastSerializer
from dmr.serializer import BaseSerializer
from server.apps.model_cursor.models import Entry
from server.apps.model_cursor.schema import (
    CursorQuery,
    EntryModel,
)


@final
class EntryAsyncController(Controller[PydanticFastSerializer]):
    """List entries using cursor-based pagination (async)."""

    async def get(
        self,
        parsed_query: Query[CursorQuery],
    ) -> CursorPaginated[EntryModel]:
        paginator = CursorPaginator(
            Entry.objects.all().order_by(*parsed_query.order_by),
            per_page=parsed_query.limit,
        )
        page = await paginator.apage(parsed_query.cursor)
        return CursorPaginated(
            next_cursor=page.next_cursor,
            per_page=paginator.per_page,
            page=[
                EntryModel.model_validate(entry) for entry in page.objects_list
            ],
        )

    @override
    async def handle_async_error(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, InvalidCursorError):
            return controller.to_error(
                controller.format_error(str(exc)),
                status_code=HTTPStatus.BAD_REQUEST,
            )
        raise exc from None


# run: {"controller": "EntryAsyncController", "method": "get", "url": "/api/entries-async/", "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "EntryAsyncController", "method": "get", "url": "/api/entries-async/", "query": "?cursor=MnwtfGF8LXwy", "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "EntryAsyncController", "method": "get", "url": "/api/entries-async/", "query": "?cursor=INVALID", "populate_db": true, "curl_args": ["-D", "-"], "assert-error-text": "cannot be decoded", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "EntryAsyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
