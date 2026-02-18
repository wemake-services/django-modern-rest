from typing import Final, NotRequired, TypedDict

import pydantic
from django.core.paginator import Paginator

from dmr import Controller, Query
from dmr.pagination import Page, Paginated
from dmr.plugins.pydantic import PydanticSerializer


class _User(pydantic.BaseModel):
    email: str


class _PageQuery(TypedDict):
    page_size: NotRequired[int]
    page: NotRequired[int]


_USERS: Final = (
    _User(email='one@example.com'),
    _User(email='two@example.com'),
    _User(email='three@example.com'),
)


class UsersController(
    Controller[PydanticSerializer],
    Query[_PageQuery],
):
    def get(self) -> Paginated[_User]:
        page = self.parsed_query.get('page', 1)
        page_size = self.parsed_query.get('page_size', 2)

        paginator = Paginator(_USERS, page_size)
        return Paginated(
            count=paginator.count,
            num_pages=paginator.num_pages,
            per_page=paginator.per_page,
            page=Page(
                number=page,
                object_list=list(paginator.page(page).object_list),
            ),
        )


# run: {"controller": "UsersController", "method": "get", "url": "/api/users/"}  # noqa: ERA001, E501
# run: {"controller": "UsersController", "method": "get", "url": "/api/users/", "query": "?page=2"}  # noqa: ERA001, E501
