from typing import Annotated

import pydantic

from dmr import Controller, FileMetadata
from dmr.openapi.objects import Encoding, MediaTypeMetadata
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer


class FileModel(pydantic.BaseModel):
    size: int = pydantic.Field(le=1024 * 5)


class UserUpload(pydantic.BaseModel):
    avatar: FileModel


class UserController(
    Controller[PydanticSerializer],
):
    parsers = (MultiPartParser(),)

    def post(
        self,
        parsed_file_metadata: FileMetadata[
            Annotated[
                UserUpload,
                MediaTypeMetadata(
                    # Note, that this can also inferred from `Literal` type
                    # in `FileModel.content_type` property, but can be set here:
                    encoding={'avatar': Encoding(content_type='image/png')},
                ),
            ]
        ],
    ) -> str:
        return 'post'


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
