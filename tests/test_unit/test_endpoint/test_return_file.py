import pathlib
from collections.abc import Iterator
from http import HTTPStatus
from typing import Final, final

import pytest
from django.http import FileResponse

from django_modern_rest import Controller, HeaderSpec, ResponseSpec, validate
from django_modern_rest.files import FileBody
from django_modern_rest.openapi.objects.enums import OpenAPIFormat
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.renderers import FileRenderer
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


def test_binary_schema() -> None:
    """Ensure that ``FileBody`` returns valid schema."""
    assert FileBody.schema().format == OpenAPIFormat.BINARY


_FILEPATH: Final = 'docs/examples/components/receipt.txt'


@final
class _FileSyncController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            FileBody,
            status_code=HTTPStatus.OK,
            headers={
                'Content-Length': HeaderSpec(),
                'Content-Disposition': HeaderSpec(),
            },
        ),
        renderers=[FileRenderer()],
    )
    def get(self) -> FileResponse:
        return FileResponse(
            pathlib.Path(_FILEPATH).open(mode='rb'),
            filename='receipt.txt',
            as_attachment=True,
            content_type='text/plain',
        )


@pytest.mark.django_db
def test_return_file_sync(dmr_rf: DMRRequestFactory) -> None:
    """Ensures we can return files from a sync endpoint."""
    request = dmr_rf.get('/whatever/')

    response = _FileSyncController.as_view()(request)

    assert isinstance(response, FileResponse)
    assert not response.is_async
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Content-Type': 'text/plain',
        'Content-Length': '16',
        'Content-Disposition': 'attachment; filename="receipt.txt"',
    }
    assert isinstance(response.streaming_content, Iterator)
    assert response.getvalue() == b'Example receipt\n'
    response.close()


@final
class _FileAsyncController(Controller[PydanticSerializer]):
    renderers = (FileRenderer('text/plain'),)

    @validate(
        ResponseSpec(
            FileBody,
            status_code=HTTPStatus.OK,
            headers={
                'Content-Length': HeaderSpec(),
                'Content-Disposition': HeaderSpec(),
            },
        ),
    )
    async def get(self) -> FileResponse:
        return FileResponse(
            # We don't care that it is sync:
            pathlib.Path(_FILEPATH).open(mode='rb'),
            filename='receipt.txt',
            as_attachment=True,
            content_type='text/plain',
        )


@pytest.mark.asyncio
async def test_return_file_async(dmr_async_rf: DMRAsyncRequestFactory) -> None:
    """Ensures we can return files from an async endpoint."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_FileAsyncController.as_view()(request))

    assert isinstance(response, FileResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Content-Type': 'text/plain',
        'Content-Length': '16',
        'Content-Disposition': 'attachment; filename="receipt.txt"',
    }
    assert isinstance(response.streaming_content, Iterator)
    assert response.getvalue() == b'Example receipt\n'
    response.close()
