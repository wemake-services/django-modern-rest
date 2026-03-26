import pathlib
from typing import Final

from django.http import FileResponse

from dmr import Controller, validate
from dmr.files import FileResponseSpec
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import FileRenderer

_FILEPATH: Final = pathlib.Path('examples/components/receipt.txt')


class FileController(Controller[PydanticSerializer]):
    @validate(
        FileResponseSpec(),
        renderers=[FileRenderer('text/plain')],
    )
    def get(self) -> FileResponse:
        return FileResponse(
            _FILEPATH.open(mode='rb'),
            filename='receipt.txt',
            as_attachment=True,
            content_type='text/plain',
        )


# run: {"controller": "FileController", "method": "get", "url": "/api/file/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "FileController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
