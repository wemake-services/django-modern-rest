import uuid
from typing import Generic, TypeVar

import pydantic

from django_modern_rest import Body, Controller
from django_modern_rest.plugins.msgspec import (
    MsgspecJsonParser,
    MsgspecJsonRenderer,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from examples.negotiation.negotiation import XmlParser, XmlRenderer


class _UserProfile(pydantic.BaseModel):
    age: int


class _UserInputData(pydantic.BaseModel):
    email: str
    profile: _UserProfile


class _UserOutputData(_UserInputData):
    uid: uuid.UUID


_ModelT = TypeVar('_ModelT')


class _UserDocument(pydantic.BaseModel, Generic[_ModelT]):
    user: _ModelT


class UserController(
    Body[_UserDocument[_UserInputData]],
    Controller[PydanticSerializer],
):
    parsers = (MsgspecJsonParser(), XmlParser())
    renderers = (MsgspecJsonRenderer(), XmlRenderer())

    def post(self) -> _UserDocument[_UserOutputData]:
        return _UserDocument(
            user=_UserOutputData(
                uid=uuid.uuid4(),
                email=self.parsed_body.user.email,
                profile=self.parsed_body.user.profile,
            ),
        )


# run: {"controller": "UserController", "method": "post", "url": "/api/user/", "headers": {"Content-Type": "application/xml", "Accept": "application/json"}, "body": {"user": {"email": "user@example.com", "profile": {"age": 28}}}}  # noqa: ERA001, E501
