from typing_extensions import TypedDict, override

from dmr.plugins.pydantic import PydanticSerializer
from examples.reusable_code.reusable_parsing import ReusableController


class _RequestModel(TypedDict):
    first_name: str
    last_name: str


class _ResponseBody(TypedDict):
    full_name: str


class PydanticController(
    ReusableController[PydanticSerializer, _RequestModel, _ResponseBody],
):
    @override
    def convert(self, parsed_body: _RequestModel) -> _ResponseBody:
        return {
            'full_name': (
                f'{parsed_body["first_name"]} {parsed_body["last_name"]}'
            ),
        }


# run: {"controller": "PydanticController", "method": "post", "body": {"first_name": "Nikita", "last_name": "Sobolev"}, "url": "/api/example/"}  # noqa: ERA001, E501
