import json
from http import HTTPMethod, HTTPStatus
from typing import ClassVar, Literal, final

import pydantic
import pytest
from django.conf import LazySettings
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory
from django.test.client import MULTIPART_CONTENT
from faker import Faker
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import Body, Controller, FileMetadata, modify
from dmr.exceptions import EndpointMetadataError
from dmr.parsers import (
    DeserializeFunc,
    MultiPartParser,
    Parser,
    Raw,
    SupportsFileParsing,
)
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _FileModel(pydantic.BaseModel):
    content_type: Literal['text/plain']
    size: int


@final
class _UploadedFiles(pydantic.BaseModel):
    receipt: _FileModel
    rules: _FileModel


@final
class _FileController(
    FileMetadata[_UploadedFiles],
    Controller[PydanticSerializer],
):
    parsers = (MultiPartParser(),)

    def post(self) -> _UploadedFiles:
        for content_key in self.parsed_file_metadata.model_fields_set:
            assert isinstance(self.request.FILES[content_key], UploadedFile)
        return self.parsed_file_metadata


def test_file_metadata(
    rf: RequestFactory,
    faker: Faker,
) -> None:
    """Ensures correct file metadata can be parsed."""
    rules = faker.name().encode('utf8')
    receipt = faker.name().encode('utf8')
    request = rf.post(
        '/whatever/',
        {
            'rules': SimpleUploadedFile('rules.txt', rules),
            'receipt': SimpleUploadedFile('receipt.txt', receipt),
        },
    )

    response = _FileController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {
        'receipt': {'content_type': 'text/plain', 'size': len(receipt)},
        'rules': {'content_type': 'text/plain', 'size': len(rules)},
    }


def test_file_metadata_wrong_content_type(
    rf: RequestFactory,
    faker: Faker,
) -> None:
    """Ensures wrong file metadata raises."""
    rules = faker.name().encode('utf8')
    receipt = faker.name().encode('utf8')
    request = rf.post(
        '/whatever/',
        {
            'rules': SimpleUploadedFile(
                'rules.txt',
                rules,
                content_type='text/rich',
            ),
            'receipt': SimpleUploadedFile('receipt.txt', receipt),
        },
    )

    response = _FileController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': "Input should be 'text/plain'",
                'loc': ['parsed_file_metadata', 'rules', 'content_type'],
                'type': 'value_error',
            },
        ],
    })


def test_file_metadata_empty(
    rf: RequestFactory,
    faker: Faker,
) -> None:
    """Ensures file metadata fields are required."""
    request = rf.post('/whatever/', {})

    response = _FileController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['parsed_file_metadata', 'receipt'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['parsed_file_metadata', 'rules'],
                'type': 'value_error',
            },
        ],
    })


@final
class _Receipt(pydantic.BaseModel):
    name: str
    content_type: Literal['text/plain']
    size: int = pydantic.Field(lt=1000)


@final
class _MultipleFiles(pydantic.BaseModel):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('receipts',))

    receipts: list[_Receipt]


@final
class _MultipleFilesController(
    FileMetadata[_MultipleFiles],
    Controller[PydanticSerializer],
):
    parsers = (MultiPartParser(),)

    def post(self) -> _MultipleFiles:
        for content_key in self.parsed_file_metadata.model_fields_set:
            assert content_key in self.request.FILES
            for file_obj in self.request.FILES.getlist(content_key):
                assert isinstance(file_obj, UploadedFile)
        return self.parsed_file_metadata


def test_file_metadata_multiple_uploads(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that we can be parse metadata of several files."""
    first = faker.name().encode('utf8')
    second = faker.name().encode('utf8')
    request = dmr_rf.post(
        '/whatever/',
        {
            'receipts': [
                SimpleUploadedFile('first.txt', first),
                SimpleUploadedFile('second.txt', second),
            ],
        },
        content_type=MULTIPART_CONTENT,
    )

    response = _MultipleFilesController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {
        'receipts': [
            {
                'name': 'first.txt',
                'content_type': 'text/plain',
                'size': len(first),
            },
            {
                'name': 'second.txt',
                'content_type': 'text/plain',
                'size': len(second),
            },
        ],
    }


def test_file_metadata_missing_parser() -> None:
    """Ensures that FileMetadata needs file parsers."""
    with pytest.raises(EndpointMetadataError, match='can parse files'):

        class _Controller(
            FileMetadata[_MultipleFiles],
            Controller[PydanticSerializer],
        ):
            def post(self) -> str:
                raise NotImplementedError


@final
class _BodyPayload(pydantic.BaseModel):
    user_id: int
    user_email: str


@final
class _OutputPayload(pydantic.BaseModel):
    receipt: _FileModel
    rules: _FileModel
    user_id: int
    user_email: str


@final
class _FileAndBodyController(
    Controller[PydanticSerializer],
    Body[_BodyPayload],
    FileMetadata[_UploadedFiles],
):
    parsers = (MultiPartParser(),)

    @modify(status_code=HTTPStatus.OK)
    def post(self) -> _OutputPayload:
        for content_key in self.parsed_file_metadata.model_fields_set:
            assert isinstance(self.request.FILES[content_key], UploadedFile)
        return _OutputPayload(
            user_id=self.parsed_body.user_id,
            user_email=self.parsed_body.user_email,
            receipt=self.parsed_file_metadata.receipt,
            rules=self.parsed_file_metadata.rules,
        )

    def put(self) -> _OutputPayload:
        for content_key in self.parsed_file_metadata.model_fields_set:
            assert isinstance(self.request.FILES[content_key], UploadedFile)
        return _OutputPayload(
            user_id=self.parsed_body.user_id,
            user_email=self.parsed_body.user_email,
            receipt=self.parsed_file_metadata.receipt,
            rules=self.parsed_file_metadata.rules,
        )

    def patch(self) -> _OutputPayload:
        for content_key in self.parsed_file_metadata.model_fields_set:
            assert isinstance(self.request.FILES[content_key], UploadedFile)
        return _OutputPayload(
            user_id=self.parsed_body.user_id,
            user_email=self.parsed_body.user_email,
            receipt=self.parsed_file_metadata.receipt,
            rules=self.parsed_file_metadata.rules,
        )


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
    ],
)
def test_send_files_with_body(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that we can send files with body."""
    raw_request_data = {
        'user_id': faker.pyint(),
        'user_email': faker.email(),
    }
    receipt = faker.name().encode('utf8')
    rules = faker.name().encode('utf8')
    request = dmr_rf.generic(
        str(method),
        '/whatever/',
        dmr_rf._encode_data(
            {
                **raw_request_data,
                'receipt': SimpleUploadedFile('receipt.txt', receipt),
                'rules': SimpleUploadedFile('rules.txt', rules),
            },
            MULTIPART_CONTENT,
        ),
        content_type=MULTIPART_CONTENT,
    )

    response = _FileAndBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {
        **raw_request_data,
        'receipt': {'content_type': 'text/plain', 'size': len(receipt)},
        'rules': {'content_type': 'text/plain', 'size': len(rules)},
    }


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
    ],
)
def test_send_files_with_body_invalid(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that we can parsing invalid form raises."""
    request = dmr_rf.generic(
        str(method),
        '/whatever/',
        b'',
        headers={
            'Content-Type': MULTIPART_CONTENT,
            'Content-Length': -1,  # <- invalid header is the cause
        },
    )

    response = _FileAndBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {'msg': 'Invalid content length: -1', 'type': 'value_error'},
        ],
    })


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
    ],
)
def test_file_metadata_too_many_files(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    settings: LazySettings,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures we can limit the number of files in the settings."""
    settings.DATA_UPLOAD_MAX_NUMBER_FILES = 1

    rules = faker.name().encode('utf8')
    receipt = faker.name().encode('utf8')
    request = dmr_rf.generic(
        str(method),
        '/whatever/',
        dmr_rf._encode_data(
            {
                'receipt': SimpleUploadedFile('receipt.txt', receipt),
                'rules': SimpleUploadedFile('rules.txt', rules),
            },
            MULTIPART_CONTENT,
        ),
        headers={'Content-Type': MULTIPART_CONTENT},
    )

    response = _FileAndBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'The number of files exceeded '
                    'settings.DATA_UPLOAD_MAX_NUMBER_FILES.'
                ),
                'type': 'value_error',
            },
        ],
    })


@final
class _WrongBodyParser(Parser):
    content_type = 'multipart/form-data'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
    ) -> None:
        raise NotImplementedError


@final
class _FakeParser(SupportsFileParsing, Parser):
    content_type = 'application/json'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
    ) -> None:
        raise NotImplementedError


@final
class _ControllerWithWrongParsers(
    Controller[PydanticSerializer],
    FileMetadata[_UploadedFiles],
):
    parsers = (_FakeParser(), _WrongBodyParser())

    def post(self) -> _OutputPayload:
        raise NotImplementedError


def test_send_files_with_body_wrong_parsers(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that when selecting non-files ready parser, it raises."""
    request = dmr_rf.post(
        '/whatever/',
        {},
        content_type=MULTIPART_CONTENT,
    )

    response = _ControllerWithWrongParsers.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    "Trying to parse files with '_WrongBodyParser' "
                    'that does not support SupportsFileParsing protocol'
                ),
                'type': 'value_error',
            },
        ],
    })


@final
class _JsonBodyPayload(pydantic.BaseModel):
    user: pydantic.Json[_BodyPayload]


@final
class _JsonOutputPayload(pydantic.BaseModel):
    receipt: _FileModel
    rules: _FileModel
    user: _BodyPayload


@final
class _FileAndJsonController(
    Controller[PydanticSerializer],
    Body[_JsonBodyPayload],
    FileMetadata[_UploadedFiles],
):
    parsers = (MultiPartParser(),)

    @modify(status_code=HTTPStatus.OK)
    def post(self) -> _JsonOutputPayload:
        for content_key in self.parsed_file_metadata.model_fields_set:
            assert isinstance(self.request.FILES[content_key], UploadedFile)
        return _JsonOutputPayload(
            user=self.parsed_body.user,
            receipt=self.parsed_file_metadata.receipt,
            rules=self.parsed_file_metadata.rules,
        )

    def put(self) -> _JsonOutputPayload:
        for content_key in self.parsed_file_metadata.model_fields_set:
            assert isinstance(self.request.FILES[content_key], UploadedFile)
        return _JsonOutputPayload(
            user=self.parsed_body.user,
            receipt=self.parsed_file_metadata.receipt,
            rules=self.parsed_file_metadata.rules,
        )


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
    ],
)
def test_send_files_with_json_body(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that we can send files with json formatted body."""
    raw_request_data = {
        'user_id': faker.pyint(),
        'user_email': faker.email(),
    }
    receipt = faker.name().encode('utf8')
    rules = faker.name().encode('utf8')
    request = dmr_rf.generic(
        str(method),
        '/whatever/',
        dmr_rf._encode_data(
            {
                'user': json.dumps(raw_request_data),
                'receipt': SimpleUploadedFile('receipt.txt', receipt),
                'rules': SimpleUploadedFile('rules.txt', rules),
            },
            MULTIPART_CONTENT,
        ),
        content_type=MULTIPART_CONTENT,
    )

    response = _FileAndJsonController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {
        'user': raw_request_data,
        'receipt': {'content_type': 'text/plain', 'size': len(receipt)},
        'rules': {'content_type': 'text/plain', 'size': len(rules)},
    }
