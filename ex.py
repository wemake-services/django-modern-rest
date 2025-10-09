from typing import reveal_type

import pydantic

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import Query, rest


class _QueryDict(pydantic.BaseModel):
    query: str


class _UserDTO(pydantic.BaseModel):
    id: int


class MyController(
    Query[_QueryDict],
    Controller,
):
    """Example controller class."""

    @rest
    def get(self, user_id: int) -> _UserDTO:
        """Example get method."""
        return _UserDTO(id=user_id)


reveal_type(MyController.get)  # noqa: WPS421
