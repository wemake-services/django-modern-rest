from typing import Generic

from typing_extensions import TypedDict, TypeVar

from dmr import Body, Controller
from dmr.serializer import BaseSerializer


class DefaultRequestModel(TypedDict):
    first_name: str
    last_name: str


_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)
_RequestModelT = TypeVar('_RequestModelT', default=DefaultRequestModel)


class ReusableController(
    Controller[_SerializerT],
    Generic[_SerializerT, _RequestModelT],
):
    def post(self, parsed_body: Body[_RequestModelT]) -> _RequestModelT:
        return parsed_body
