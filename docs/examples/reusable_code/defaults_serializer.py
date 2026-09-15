from typing import Generic

from typing_extensions import TypedDict, TypeVar

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer


class _RequestModel(TypedDict):
    first_name: str
    last_name: str


_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
    default=PydanticSerializer,
)
_RequestModelT = TypeVar('_RequestModelT', default=_RequestModel)


class ReusableController(
    Controller[_SerializerT],
    Generic[_SerializerT, _RequestModelT],
):
    """Still abstract: its own type variables are not exact types."""

    def post(self, parsed_body: Body[_RequestModelT]) -> _RequestModelT:
        return parsed_body


class PydanticController(ReusableController):
    """Concrete: both type variables fall back to their defaults."""


# run: {"controller": "PydanticController", "method": "post", "body": {"first_name": "Nikita", "last_name": "Sobolev"}, "url": "/api/example/"}  # noqa: ERA001, E501
