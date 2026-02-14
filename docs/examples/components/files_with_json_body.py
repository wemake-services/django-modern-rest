from typing import Literal

import pydantic

from django_modern_rest import Body, Controller, FileMetadata
from django_modern_rest.parsers import MultiPartParser
from django_modern_rest.plugins.pydantic import PydanticSerializer


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


class FileAndJsonController(
    Controller[PydanticSerializer],
    Body[_JsonBodyPayload],
    FileMetadata[_UploadedFiles],
):
    parsers = (MultiPartParser(),)

    def put(self) -> _JsonOutputPayload:
        return _JsonOutputPayload(
            user=self.parsed_body.user,
            receipt=self.parsed_file_metadata.receipt,
            rules=self.parsed_file_metadata.rules,
        )


# run: {"controller": "FileAndJsonController", "url": "/api/users/", "method": "put", "headers": {"Content-Type": "multipart/form-data"}, "files": {"receipt": "receipt.txt", "rules": "rules.txt"}, "body": {"user": "{\"user_id\": 1, \"user_email\": \"example@mail.com\"}"}}  # noqa: ERA001, E501
