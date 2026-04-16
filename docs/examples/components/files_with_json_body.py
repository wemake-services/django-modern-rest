from typing import Literal

import pydantic

from dmr import Body, Controller, FileMetadata
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer


class _FileModel(pydantic.BaseModel):
    content_type: Literal['text/plain']
    size: int


class _UploadedFiles(pydantic.BaseModel):
    receipt: _FileModel
    rules: _FileModel


class _BodyPayload(pydantic.BaseModel):
    user_id: int
    user_email: str


class _JsonBodyPayload(pydantic.BaseModel):
    user: pydantic.Json[_BodyPayload]


class _JsonOutputPayload(pydantic.BaseModel):
    receipt: _FileModel
    rules: _FileModel
    user: _BodyPayload


class FileAndJsonController(Controller[PydanticSerializer]):
    parsers = (MultiPartParser(),)

    def put(
        self,
        parsed_body: Body[_JsonBodyPayload],
        parsed_file_metadata: FileMetadata[_UploadedFiles],
    ) -> _JsonOutputPayload:
        return _JsonOutputPayload(
            user=parsed_body.user,
            receipt=parsed_file_metadata.receipt,
            rules=parsed_file_metadata.rules,
        )


# run: {"controller": "FileAndJsonController", "url": "/api/users/", "method": "put", "headers": {"Content-Type": "multipart/form-data"}, "files": {"receipt": "receipt.txt", "rules": "rules.txt"}, "body": {"user": "{\"user_id\": 1, \"user_email\": \"example@mail.com\"}"}}  # noqa: ERA001, E501
