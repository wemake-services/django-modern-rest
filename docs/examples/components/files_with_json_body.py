from typing import Literal, final

import pydantic

from django_modern_rest import Body, Controller, FileMetadata
from django_modern_rest.parsers import MultiPartParser
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class _FileModel(pydantic.BaseModel):
    content_type: Literal['text/plain']
    size: int


@final
class _UploadedFiles(pydantic.BaseModel):
    receipt: _FileModel
    rules: _FileModel


@final
class _BodyPayload(pydantic.BaseModel):
    user_id: int
    user_email: str


@final
class _JsonBodyPayload(pydantic.BaseModel):
    user: pydantic.Json[_BodyPayload]


@final
class _JsonOutputPayload(pydantic.BaseModel):
    receipt: _FileModel
    rules: _FileModel
    user: _BodyPayload


@final
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
