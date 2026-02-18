from typing import Literal

import pydantic
from django.core.files.uploadedfile import UploadedFile

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


class _OutputPayload(pydantic.BaseModel):
    receipt: _FileModel
    rules: _FileModel
    user_id: int
    user_email: str


class FileAndBodyController(
    Controller[PydanticSerializer],
    Body[_BodyPayload],
    FileMetadata[_UploadedFiles],
):
    parsers = (MultiPartParser(),)

    def post(self) -> _OutputPayload:
        for content_key in self.parsed_file_metadata.model_fields_set:
            assert isinstance(self.request.FILES[content_key], UploadedFile)
        return _OutputPayload(
            user_id=self.parsed_body.user_id,
            user_email=self.parsed_body.user_email,
            receipt=self.parsed_file_metadata.receipt,
            rules=self.parsed_file_metadata.rules,
        )


# run: {"controller": "FileAndBodyController", "url": "/api/users/", "method": "post", "headers": {"Content-Type": "multipart/form-data"}, "files": {"receipt": "receipt.txt", "rules": "rules.txt"}, "body": {"user_id": 1, "user_email": "example@mail.com"}}  # noqa: ERA001, E501
