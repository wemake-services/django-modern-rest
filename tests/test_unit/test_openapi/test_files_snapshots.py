import json
import re
from typing import Annotated, Any, ClassVar, Final, Literal, TypeAlias

import pydantic
from django.http import FileResponse
from django.urls import path
from inline_snapshot import snapshot
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


class _OneFile(pydantic.BaseModel):
    first_file: _FileModel


class _OptionalFileController(Controller[PydanticSerializer]):
    parsers = (MultiPartParser(), JsonParser())

    async def post(
        self,
        parsed_body: Body[dict[str, str]],
        # A default makes this component optional, so a request without
        # any files is valid. `JsonParser` cannot parse files, but an
        # `application/json` request simply arrives without them:
        parsed_file_metadata: FileMetadata[_OneFile | None] = None,
    ) -> str:
        raise NotImplementedError


_MULTIPART: Final = str(ContentType.multipart_form_data)
_SCHEMAS_PREFIX: Final = '#/components/schemas/'


def _built_document(
    controller: type[Controller[PydanticSerializer]],
) -> Any:
    return build_schema(
        Router('', [path('merged/', controller.as_view())]),
    ).convert()


def _merged_request_body(
    controller: type[Controller[PydanticSerializer]],
) -> Any:
    document = _built_document(controller)
    return document['paths']['/merged/']['post']['requestBody']


def test_required_file_merged_body() -> None:
    """Ensure that a required file component rules out `application/json`."""
    # `FileMetadata[]` is required here, so it has to parse every request,
    # and `JsonParser` cannot parse files. Sending `application/json`
    # to this endpoint is a `400`, so it is not documented.
    assert _merged_request_body(_BodyFirstController) == snapshot({
        'content': {
            'multipart/form-data': {
                'schema': {
                    'allOf': [
                        {
                            'additionalProperties': {'type': 'string'},
                            'type': 'object',
                        },
                        {
                            'properties': {
                                'first_file': {
                                    'type': 'string',
                                    'format': 'binary',
                                },
                                'second_file': {
                                    'type': 'string',
                                    'format': 'binary',
                                },
                            },
                            'type': 'object',
                            'required': ['first_file', 'second_file'],
                            'title': '_SeveralSimpleFiles',
                        },
                    ],
                },
                'encoding': {
                    'first_file': {
                        'contentType': 'application/json, text/plain',
                    },
                    'second_file': {
                        'contentType': 'application/json, text/plain',
                    },
                },
            },
        },
        'required': True,
    })


def test_optional_file_merged_body() -> None:
    """Ensure that an optional file component keeps `application/json`."""
    assert _merged_request_body(_OptionalFileController) == snapshot({
        'content': {
            'application/json': {
                'schema': {
                    'additionalProperties': {'type': 'string'},
                    'type': 'object',
                },
            },
            'multipart/form-data': {
                'schema': {
                    'allOf': [
                        {
                            'additionalProperties': {'type': 'string'},
                            'type': 'object',
                        },
                        {
                            'anyOf': [
                                {
                                    'properties': {
                                        'first_file': {
                                            'type': 'string',
                                            'format': 'binary',
                                        },
                                    },
                                    'type': 'object',
                                    'required': ['first_file'],
                                    'title': '_OneFile',
                                },
                                {'type': 'null'},
                            ],
                        },
                    ],
                },
            },
        },
        'required': True,
    })


def test_file_model_is_inlined_not_referenced() -> None:
    """Ensure that a file model does not leave a `$ref` to nothing."""
    document = _built_document(_OptionalFileController)
    registered = document['components']['schemas']

    # `FileMetadata[]` swaps its model for the file representation, so
    # `_OneFile` is inlined and never becomes a component on its own.
    # Referencing it anyway would leave a `$ref` that resolves to nothing,
    # which `openapi-spec-validator` does not catch:
    dangling = {
        ref
        for ref in re.findall(r'"\$ref": "(.+?)"', json.dumps(document))
        if ref.removeprefix(_SCHEMAS_PREFIX) not in registered
    }

    assert '_OneFile' not in registered
    assert dangling == set()


def test_merged_body_ignores_component_order() -> None:
    """Ensure that component order does not change the merged body."""
    file_first = _merged_request_body(_FileFirstController)
    body_first = _merged_request_body(_BodyFirstController)
    # `allOf` lists the component schemas in declaration order, and the
    # order of its members does not change what it allows. Everything
    # else used to depend on which component came last:
    for body in (file_first, body_first):
        multipart = body['content'][_MULTIPART]
        multipart['schema']['allOf'].sort(key=repr)

    assert file_first == body_first
