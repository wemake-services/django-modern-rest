import json
from http import HTTPStatus
from typing import ClassVar, Literal, final

import pydantic
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.http import HttpResponse
from django.test import RequestFactory
from django.test.client import MULTIPART_CONTENT
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest import Controller, FileMetadata
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.parsers import MultiPartParser
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


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
