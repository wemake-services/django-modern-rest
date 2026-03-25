import json
from typing import Annotated, ClassVar, Literal

import pydantic
from django.http import FileResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import (
    Body,
    Controller,
    FileMetadata,
    modify,
    validate,
)
from dmr.files import FileResponseSpec
from dmr.openapi import build_schema
from dmr.openapi.objects import Encoding, MediaTypeMetadata
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import FileRenderer
from dmr.routing import Router


class _FileModel(pydantic.BaseModel):
    content_type: Literal['application/json', 'text/plain']
    size: int


class _SeveralFiles(pydantic.BaseModel):
    """Model docs."""

    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('attachments',))

    attachments: list[_FileModel]
    second_file: _FileModel


class _FileController(
    Controller[PydanticSerializer],
):
    parsers = (MultiPartParser(),)

    @modify(operation_id='file_test_id', deprecated=True)
    async def get(
        self,
        parsed_file_metadata: FileMetadata[_SeveralFiles],
    ) -> list[int]:
        raise NotImplementedError


def test_file_request_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for file controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [path('file/', _FileController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _FileResponseController(Controller[PydanticSerializer]):
    @validate(
        FileResponseSpec(),
        renderers=[FileRenderer('image/png')],
    )
    async def get(self) -> FileResponse:
        raise NotImplementedError


def test_file_response_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for file response controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [path('file-response/', _FileResponseController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _DescriptionModel(pydantic.BaseModel):
    """Description from doc."""

    first: str
    second: list[int]


class _BodyAndFileController(
    Controller[PydanticSerializer],
):
    parsers = (MultiPartParser(),)

    async def post(
        self,
        parsed_body: Body[_DescriptionModel],
        parsed_file_metadata: FileMetadata[_SeveralFiles],
    ) -> list[int]:
        raise NotImplementedError


def test_body_and_file_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for file controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '/',
                    [path('file/', _BodyAndFileController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _FileMetadataController(
    Controller[PydanticSerializer],
):
    parsers = (MultiPartParser(),)

    async def get(
        self,
        parsed_file_metadata: FileMetadata[
            Annotated[
                _SeveralFiles,
                MediaTypeMetadata(
                    example='whatever',
                    encoding={
                        'second_file': Encoding(content_type='image/png'),
                        'attachments': Encoding(content_type='image/jpg'),
                    },
                ),
            ]
        ],
    ) -> list[int]:
        raise NotImplementedError


def test_file_with_metadata_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for file controller with metadata."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [
                        path(
                            'file-with-metadata/',
                            _FileMetadataController.as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
