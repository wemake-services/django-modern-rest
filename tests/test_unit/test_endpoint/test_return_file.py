import io
import pathlib
from collections.abc import Iterator
from contextlib import closing
from http import HTTPStatus
from typing import Final, final

import pytest
from django.http import FileResponse

from dmr import Controller, validate
from dmr.files import FileResponseSpec
from dmr.headers import HeaderSpec
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import FileRenderer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_FILEPATH: Final = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / 'docs/examples/components/receipt.txt'
)

_FILE_CONTENT: Final = _FILEPATH.read_bytes()
# win32 uses `\r\n` as a line break, others use `\n`:
_CONTENT_LENGTH: Final = str(len(_FILE_CONTENT))


@final
class _FileSyncController(Controller[PydanticSerializer]):
    @validate(
        FileResponseSpec(as_attachment=True),
        renderers=[FileRenderer()],
    )
    def get(self) -> FileResponse:
        return FileResponse(
            pathlib.Path(_FILEPATH).open(mode='rb'),
            filename='receipt.txt',
            as_attachment=True,
            content_type='text/plain',
        )


@final
class _InlineFileSyncController(Controller[PydanticSerializer]):
    @validate(
        FileResponseSpec(),
        renderers=[FileRenderer('text/plain')],
    )
    def get(self) -> FileResponse:
        return FileResponse(
            io.BytesIO(b'Hello'),
            content_type='text/plain',
        )


@final
class _RegularBodyWithFileRendererController(Controller[PydanticSerializer]):
    renderers = (FileRenderer(),)

    def get(self) -> dict[str, str]:
        return {'detail': 'not a file'}


@pytest.mark.django_db
def test_return_file_sync(dmr_rf: DMRRequestFactory) -> None:
    """Ensures we can return files from a sync endpoint."""
    request = dmr_rf.get('/whatever/')

    response = _FileSyncController.as_view()(request)

    with closing(response):
        assert isinstance(response, FileResponse)
        assert not response.is_async
        assert response.status_code == HTTPStatus.OK
        assert response.headers == {
            'Content-Type': 'text/plain',
            'Content-Length': _CONTENT_LENGTH,
            'Content-Disposition': 'attachment; filename="receipt.txt"',
        }
        assert isinstance(response.streaming_content, Iterator)
        assert response.getvalue() == _FILE_CONTENT


@pytest.mark.django_db
def test_return_file_without_attachment_sync(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures file responses do not require ``as_attachment``."""
    request = dmr_rf.get('/whatever/')

    response = _InlineFileSyncController.as_view()(request)

    with closing(response):
        assert isinstance(response, FileResponse)
        assert response.status_code == HTTPStatus.OK
        assert response.headers == {
            'Content-Type': 'text/plain',
            'Content-Length': '5',
        }
        assert isinstance(response.streaming_content, Iterator)
        assert response.getvalue() == b'Hello'


def test_file_renderer_render_error(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures file renderer errors explain how to return regular data."""
    request = dmr_rf.get('/whatever/')

    with pytest.raises(
        NotImplementedError,
        match=('FileRenderer cannot serialize regular response bodies'),
    ):
        _RegularBodyWithFileRendererController.as_view()(request)


def test_file_attachment_headers() -> None:
    """Ensures attachment responses require ``Content-Disposition``."""
    spec = FileResponseSpec(as_attachment=True, headers=None)

    assert spec.headers == {
        'Content-Length': HeaderSpec(),
        'Content-Disposition': HeaderSpec(),
    }


@final
class _FileAsyncController(Controller[PydanticSerializer]):
    renderers = (FileRenderer('text/plain'),)

    @validate(FileResponseSpec(as_attachment=True))
    async def get(self) -> FileResponse:
        return FileResponse(
            # We don't care that it is sync:
            pathlib.Path(_FILEPATH).open(mode='rb'),  # noqa: ASYNC230
            filename='receipt.txt',
            as_attachment=True,
            content_type='text/plain',
        )


@pytest.mark.asyncio
async def test_return_file_async(dmr_async_rf: DMRAsyncRequestFactory) -> None:
    """Ensures we can return files from an async endpoint."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_FileAsyncController.as_view()(request))

    with closing(response):
        assert isinstance(response, FileResponse)
        assert response.status_code == HTTPStatus.OK
        assert response.headers == {
            'Content-Type': 'text/plain',
            'Content-Length': _CONTENT_LENGTH,
            'Content-Disposition': 'attachment; filename="receipt.txt"',
        }
        assert isinstance(response.streaming_content, Iterator)
        assert response.getvalue() == _FILE_CONTENT
