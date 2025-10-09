import pydantic
from typing_extensions import reveal_type

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import Body, Headers, Query, rest


class _QueryDict(pydantic.BaseModel):
    query: str


class _Headers(pydantic.BaseModel):
    token: str = pydantic.Field(alias='X-Token')


class _UserInputDTO(pydantic.BaseModel):
    email: str


class _UserDTO(pydantic.BaseModel):
    id: int


class MyController(  # noqa: WPS215
    Query[_QueryDict],
    Body[_UserInputDTO],
    Headers[_Headers],
    Controller,
):
    """Example controller class."""

    @rest
    def post(self, user_id: int) -> _UserDTO:
        """Example method."""
        reveal_type(self.parsed_query)  # noqa: WPS421  # N: Revealed type is "ex._QueryDict"
        reveal_type(self.parsed_body)  # noqa: WPS421  # N: Revealed type is "ex._UserInputDTO"
        reveal_type(self.parsed_headers)  # noqa: WPS421  # N: Revealed type is "ex._Headers"
        return _UserDTO(id=user_id)


# N: Revealed type is
# "def (ex.MyController, django.http.request.HttpRequest, user_id: builtins.int)
#  -> django.http.response.HttpResponse"
reveal_type(MyController.post)  # noqa: WPS421
