import json
from typing import Annotated, ClassVar, Literal, TypeAlias

import pydantic
from django.http import FileResponse
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Body, Controller, FileMetadata, modify, validate
from dmr.files import FileResponseSpec
from dmr.negotiation import ContentType, conditional_type
from dmr.openapi import build_schema
from dmr.openapi.objects import Encoding, MediaTypeMetadata
from dmr.parsers import JsonParser, MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import FileRenderer
from dmr.routing import Router
from dmr.settings import HttpSpec
from tests.infra.octet import OCTET_STREAM, OctetFileModel, OctetStreamParser


class _FileModel(pydantic.BaseModel):
    content_type: Literal['application/json', 'text/plain']
    size: int


class _SeveralFiles(pydantic.BaseModel):
    """Model docs."""

    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('attachments',))

    attachments: list[_FileModel]
    second_file: _FileModel


class _FileController(Controller[PydanticSerializer]):
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
        no_validate_http_spec={HttpSpec.header_name_server_managed},
    )
    async def get(self) -> FileResponse:
        raise NotImplementedError


class _AttachmentFileResponseController(Controller[PydanticSerializer]):
    @validate(
        FileResponseSpec(as_attachment=True),
        renderers=[FileRenderer('image/png')],
        no_validate_http_spec={HttpSpec.header_name_server_managed},
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


def test_attachment_file_response_schema(
    snapshot: SnapshotAssertion,
) -> None:
    """Ensure attachment file response schema has disposition header."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [
                        path(
                            'file-attachment-response/',
                            _AttachmentFileResponseController.as_view(),
                        ),
                    ],
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


class _BodyAndFileController(Controller[PydanticSerializer]):
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


class _FileMetadataController(Controller[PydanticSerializer]):
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


class _SeveralSimpleFiles(pydantic.BaseModel):
    first_file: _FileModel
    second_file: _FileModel


class _OctetFileMeta(pydantic.BaseModel):
    content_type: Literal['application/octet-stream']
    size: int
    name: str


_ConditionalUploadedFiles: TypeAlias = Annotated[
    _SeveralSimpleFiles | OctetFileModel[_OctetFileMeta],
    conditional_type({
        ContentType.multipart_form_data: _SeveralSimpleFiles,
        OCTET_STREAM: OctetFileModel[_OctetFileMeta],
    }),
]


class _ConditionalFileController(Controller[PydanticSerializer]):
    parsers = (MultiPartParser(), OctetStreamParser())

    def post(
        self,
        parsed_file_metadata: FileMetadata[_ConditionalUploadedFiles],
    ) -> str:
        raise NotImplementedError


def test_conditional_files_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for conditional files."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [
                        path(
                            'conditional-files/',
                            _ConditionalFileController.as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _SeveralParsersController(Controller[PydanticSerializer]):
    parsers = (MultiPartParser(), JsonParser())

    def post(
        self,
        # `JsonParser` can't parse files, so it must not be present:
        parsed_file_metadata: FileMetadata[_SeveralSimpleFiles],
    ) -> str:
        raise NotImplementedError

    def put(self, parsed_body: Body[dict[str, str]]) -> str:
        raise NotImplementedError


def test_several_parsers_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for controller using several parsers."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [
                        path(
                            'several-parsers/',
                            _SeveralParsersController.as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _BodyAndFileNoDocsController(Controller[PydanticSerializer]):
    parsers = (MultiPartParser(),)

    async def post(
        self,
        parsed_body: Body[dict[str, str]],
        parsed_file_metadata: FileMetadata[_SeveralSimpleFiles],
    ) -> str:
        raise NotImplementedError


def test_merged_body_without_description_schema(
    snapshot: SnapshotAssertion,
) -> None:
    """Ensure that merged request body does not have an empty description."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    '',
                    [
                        path(
                            'merged-no-description/',
                            _BodyAndFileNoDocsController.as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _FileFirstController(Controller[PydanticSerializer]):
    # `JsonParser` cannot parse files, so `Body[]` alone would document
    # `application/json`, while `FileMetadata[]` would not:
    parsers = (MultiPartParser(), JsonParser())

    async def post(
        self,
        parsed_file_metadata: FileMetadata[_SeveralSimpleFiles],
        parsed_body: Body[dict[str, str]],
    ) -> str:
        raise NotImplementedError


class _BodyFirstController(Controller[PydanticSerializer]):
    parsers = (MultiPartParser(), JsonParser())

    async def post(
        self,
        parsed_body: Body[dict[str, str]],
        parsed_file_metadata: FileMetadata[_SeveralSimpleFiles],
    ) -> str:
        raise NotImplementedError


def _merged_body_content(
    controller: type[Controller[PydanticSerializer]],
) -> dict[str, object]:
    schema = build_schema(
        Router('', [path('merged/', controller.as_view())]),
    ).convert()
    operation = schema['paths']['/merged/']['post']
    return operation['requestBody']['content']  # type: ignore[no-any-return]


def test_merged_body_content_types_ignore_order() -> None:
    """Ensure that component order does not change the documented types."""
    file_first = _merged_body_content(_FileFirstController)
    body_first = _merged_body_content(_BodyFirstController)

    # `application/json` is dropped: `FileMetadata[]` rejects `JsonParser`
    # at runtime, so such a request could never succeed.
    assert list(file_first) == [str(ContentType.multipart_form_data)]
    assert list(body_first) == list(file_first)


def test_merged_body_keeps_encoding_in_any_order() -> None:
    """Ensure that no component loses its metadata to the merge."""
    multipart = str(ContentType.multipart_form_data)
    file_first = _merged_body_content(_FileFirstController)[multipart]
    body_first = _merged_body_content(_BodyFirstController)[multipart]

    # `encoding` is only set by `FileMetadata[]`, it used to be lost
    # when `Body[]` was the one declared last:
    assert file_first['encoding'] == body_first['encoding']  # type: ignore[index]
